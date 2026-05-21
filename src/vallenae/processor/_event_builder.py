from __future__ import annotations

import math
from collections.abc import Container, Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import IntEnum
from typing import cast

from ..io.datatypes import HitFlags, HitRecord


class ChannelFunction(IntEnum):
    """
    Per-channel role used by the Event Builder.

    Matches the channel function assignment of VisualAE's Location Settings dialog.
    """

    #: Channel is excluded from event building entirely.
    UNUSED = 0
    #: Channel participates in event building and can start an event.
    NORMAL = 1
    #: Inhibits event building for FHCDT when this would be the first-hit channel;
    #: included as a subsequent hit if an event is already open.
    GUARD = 2
    #: Acts as `ChannelFunction.GUARD` when it would be the first-hit channel;
    #: acts as `ChannelFunction.NORMAL` otherwise.
    COMBINED = 3


class EventCloseReason(IntEnum):
    """Reason the Event Builder closed an event data set."""

    #: Time between first-hit and last seen exceeded DT1X-Max.
    DT1X_EXPIRED = 1
    #: Time between two consecutive hits exceeded DTNX-Max.
    DTNX_EXPIRED = 2
    #: A channel produced a second hit while `allow_multiple_hits_per_channel` was disabled.
    DUPLICATE_CHANNEL = 3
    #: No more hits available; emitted by `flush`.
    END_OF_STREAM = 4


@dataclass
class Event:
    """
    Event data set produced by the `EventBuilder`.

    An event represents the group of hits assigned to one acoustic-emission source by the Event
    Builder. Hits are time-sorted and the first hit (`hits[0]`) is always the Start-of-Event (SoE).
    """

    hits: list[HitRecord]  #: Hits assigned to this event, time-sorted; `hits[0]` is the SoE.
    close_reason: EventCloseReason  #: Why the event was closed.

    @property
    def time(self) -> float:
        """Time of the Start-of-Event in seconds (= `hits[0].time`)."""
        return self.hits[0].time

    @property
    def first_hit_channel(self) -> int:
        """First-hit channel (1.CH in VisualAE), equal to `hits[0].channel`."""
        return self.hits[0].channel

    @property
    def channel_sequence(self) -> list[int]:
        """Channels in the order they were hit (1.CH..n.CH in VisualAE)."""
        return [hit.channel for hit in self.hits]

    @property
    def dt_to_first(self) -> list[float]:
        """
        Time differences between the first hit and each subsequent hit in seconds.

        Corresponds to VisualAE's DT12..DT1n.
        Length is `len(hits) - 1` (empty for a single-hit event).
        """
        t0 = self.hits[0].time
        return [hit.time - t0 for hit in self.hits[1:]]


@dataclass
class EventBuilder:
    """
    Group hits into `Event` data sets using the VisualAE Event Builder algorithm.

    Channel functions (Normal / Guard / Combined / Unused) are honoured. A guard hit (or a
    combined hit when it would be the first-hit channel) while no event is open inhibits event
    opening for the next `fhcdt`; a guard or combined hit during an open event is included in
    that event's `Event.hits` (the downstream location processor is responsible for excluding it
    from location calculation).

    The Event Builder is a synchronous state machine. Hits must be fed in time-sorted order.
    Out-of-order input raises `ValueError`.

    Args:
        fhcdt: First Hit Channel Discrimination Time, in seconds. The gap required before a hit
            qualifies as Start-of-Event (SoE). Every hit on a listed channel resets this gap timer.
        dt1x_max: Maximum time between SoE and last hit in event, in seconds. Defines the overall
            event window starting at the SoE.
        dtnx_max: Maximum time between consecutive hits in event, in seconds. The hit-to-hit
            continuity window. Setting `dtnx_max == dt1x_max` effectively deactivates this
            criterion.
        channels: Channels to consider. Accepts three forms:

            - `None` (default): accept all channels; treat every hit as `ChannelFunction.NORMAL`.
              Hits on unknown channels are included as normal hits.
            - An iterable of channel numbers (e.g. `[1, 2, 3]`): only those channels participate,
              all as `ChannelFunction.NORMAL`. Hits on other channels are dropped.
            - A mapping of channel number to `ChannelFunction`: full per-channel control.
              Channels not present are treated as `ChannelFunction.UNUSED` and dropped.
        allow_multiple_hits_per_channel: If `False` (default), a second hit on a channel already
            represented in the open event closes the event with
            `EventCloseReason.DUPLICATE_CHANNEL`; the duplicate hit is not used for the closing
            event nor for the next one.
            If `True`, subsequent hits on a channel are kept in the event.

    Example:
        >>> from vallenae.processor import EventBuilder
        >>> builder = EventBuilder(fhcdt=2e-3, dt1x_max=2e-3, dtnx_max=2e-3)
        >>> events = list(builder.process_all(pridb.iread_hits()))  # doctest: +SKIP
    """

    fhcdt: float
    dt1x_max: float
    dtnx_max: float
    channels: Mapping[int, ChannelFunction] | Container[int] | None = None
    allow_multiple_hits_per_channel: bool = False

    def __post_init__(self) -> None:
        self._open_event: list[HitRecord] | None = None
        self._t_last_seen: float = -math.inf  # time of last listed hit (resets FHCDT timer)
        self._t_last_input: float | None = None  # monotonicity check

    def _channel_function(self, channel: int) -> ChannelFunction:
        channels = self.channels
        if channels is None:
            return ChannelFunction.NORMAL
        if isinstance(channels, Mapping):
            mapping = cast("Mapping[int, ChannelFunction]", channels)
            return mapping.get(channel, ChannelFunction.UNUSED)
        return ChannelFunction.NORMAL if channel in channels else ChannelFunction.UNUSED

    def process(self, hit: HitRecord) -> list[Event]:
        """
        Feed a single hit into the state machine.

        Returns events that became ready as a direct consequence of this hit (0 or 1 events).
        Use `flush` at the end of the stream to drain any still-open event.
        """
        if self._t_last_input is not None and hit.time < self._t_last_input:
            raise ValueError(
                f"hits must be time-sorted: got hit at t={hit.time:g} "
                f"after t={self._t_last_input:g}"
            )
        self._t_last_input = hit.time

        func = self._channel_function(hit.channel)
        if func == ChannelFunction.UNUSED:
            return []

        if self._open_event is None:
            self._try_start_event(hit, func)
            return []

        if hit.time - self._open_event[0].time > self.dt1x_max:
            closed = self._close_event(EventCloseReason.DT1X_EXPIRED)
            self._try_start_event(hit, func)
            return [closed]
        if hit.time - self._open_event[-1].time > self.dtnx_max:
            closed = self._close_event(EventCloseReason.DTNX_EXPIRED)
            self._try_start_event(hit, func)
            return [closed]
        if not self.allow_multiple_hits_per_channel and any(
            h.channel == hit.channel for h in self._open_event
        ):
            closed = self._close_event(EventCloseReason.DUPLICATE_CHANNEL)
            # Per VisualAE: the offending hit is not used for the closing event nor the next one.
            # Still update _t_last_seen since this hit is on a listed channel and affects future
            # FHCDT gap calculation.
            self._t_last_seen = hit.time
            return [closed]

        self._open_event.append(hit)
        return []

    def process_all(self, hits: Iterable[HitRecord]) -> Iterator[Event]:
        """
        Feed an iterable of hits and yield events as they close.

        Equivalent to calling `process` on each hit followed by `flush` at the end.
        The end-of-stream flush is automatic.
        """
        for hit in hits:
            yield from self.process(hit)
        yield from self.flush()

    def flush(self) -> list[Event]:
        """
        Emit the in-flight event (if any) and reset state.

        Returns the closed event with `EventCloseReason.END_OF_STREAM`, or an empty list if no event
        was open. After calling, the builder is ready for a fresh stream. Idempotent — a second
        call without intervening input returns `[]`.
        """
        closed: list[Event] = []
        if self._open_event is not None:
            closed.append(self._close_event(EventCloseReason.END_OF_STREAM))
        self._t_last_seen = -math.inf
        self._t_last_input = None
        return closed

    def _try_start_event(self, hit: HitRecord, func: ChannelFunction) -> None:
        """Try to start a new event from `hit`. Always updates `_t_last_seen`."""
        prev_t = self._t_last_seen
        self._t_last_seen = hit.time

        if func != ChannelFunction.NORMAL:
            return  # GUARD or COMBINED — inhibits, does not start an event
        if hit.status & HitFlags.AFTER_TIMEOUT:
            return  # A-flag — can never be SoE
        if hit.time - prev_t <= self.fhcdt:
            return  # FHCDT gap not satisfied

        self._open_event = [hit]

    def _close_event(self, reason: EventCloseReason) -> Event:
        assert self._open_event is not None
        # Snapshot the last in-event hit time so the next SoE check has the right FHCDT reference.
        self._t_last_seen = self._open_event[-1].time
        event = Event(hits=self._open_event, close_reason=reason)
        self._open_event = None
        return event
