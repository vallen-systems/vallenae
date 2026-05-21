from __future__ import annotations

import pytest

from vallenae.io import HitFlags, HitRecord
from vallenae.processor import ChannelFunction, EventBuilder, EventCloseReason


def make_hit(time: float, channel: int, *, status: HitFlags | None = None) -> HitRecord:
    return HitRecord(
        time=time,
        channel=channel,
        param_id=1,
        amplitude=0.1,
        duration=1e-4,
        energy=1.0,
        rms=0.01,
        status=status if status is not None else HitFlags(0),
    )


def test_short_gap_does_not_start_new_event():
    builder = EventBuilder(fhcdt=2e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    # Two hits 1 ms apart on different channels; second should not be a new SoE,
    # it should join the open event.
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert len(events[0].hits) == 2


def test_gap_greater_than_fhcdt_starts_new_event():
    builder = EventBuilder(fhcdt=2e-3, dt1x_max=1e-3, dtnx_max=1e-3)
    # First event ends after t=0 (single hit, then DT1X expires); second hit
    # at 5 ms is > FHCDT after the first => new SoE.
    hits = [make_hit(0.0, 1), make_hit(5e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 2
    assert events[0].first_hit_channel == 1
    assert events[1].first_hit_channel == 2


def test_dt1x_max_closes_event():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=2e-3, dtnx_max=10e-3)
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2), make_hit(3e-3, 3)]
    events = list(builder.process_all(hits))
    # DT1X expires at 3ms (> 2ms after SoE), closes event of hits [ch1, ch2].
    # Then hit 3 is re-evaluated: gap from last in-event hit (1ms) to 3ms is 2ms > fhcdt=0.5ms,
    # so it becomes a new SoE.
    assert len(events) == 2
    assert events[0].close_reason == EventCloseReason.DT1X_EXPIRED
    assert [h.channel for h in events[0].hits] == [1, 2]
    assert events[1].first_hit_channel == 3


def test_dtnx_max_closes_event():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=100e-3, dtnx_max=2e-3)
    # Hits at 0, 1ms, 5ms — third hit is > DTNX-Max from previous => closes event.
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2), make_hit(5e-3, 3)]
    events = list(builder.process_all(hits))
    assert len(events) == 2
    assert events[0].close_reason == EventCloseReason.DTNX_EXPIRED
    assert [h.channel for h in events[0].hits] == [1, 2]


def test_dtnx_equal_dt1x_disables_dtnx():
    # When dtnx_max == dt1x_max, DTNX cannot expire before DT1X, so it's effectively disabled.
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    hits = [make_hit(0.0, 1), make_hit(5e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert len(events[0].hits) == 2


def test_duplicate_channel_closes_event():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2), make_hit(2e-3, 1)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert events[0].close_reason == EventCloseReason.DUPLICATE_CHANNEL
    assert [h.channel for h in events[0].hits] == [1, 2]


def test_duplicate_channel_drops_offending_hit():
    # The duplicate hit should not appear in the next event either.
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    hits = [
        make_hit(0.0, 1),
        make_hit(1e-3, 2),
        make_hit(2e-3, 1),  # duplicate -> closes event, dropped
        make_hit(5e-3, 3),  # gap from 2ms is 3ms > fhcdt -> new SoE
    ]
    events = list(builder.process_all(hits))
    assert len(events) == 2
    assert events[0].close_reason == EventCloseReason.DUPLICATE_CHANNEL
    # Make sure the dropped hit is not in the second event
    assert all(h.channel != 1 or h.time != 2e-3 for h in events[1].hits)
    assert events[1].first_hit_channel == 3


def test_allow_multiple_hits_per_channel():
    builder = EventBuilder(
        fhcdt=0.5e-3,
        dt1x_max=10e-3,
        dtnx_max=10e-3,
        allow_multiple_hits_per_channel=True,
    )
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2), make_hit(2e-3, 1)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert len(events[0].hits) == 3
    assert [h.channel for h in events[0].hits] == [1, 2, 1]


def test_guard_as_first_hit_inhibits_event_opening():
    builder = EventBuilder(
        fhcdt=2e-3,
        dt1x_max=10e-3,
        dtnx_max=10e-3,
        channels={1: ChannelFunction.GUARD, 2: ChannelFunction.NORMAL},
    )
    # Guard hit at t=0 -> inhibits event opening.
    # Normal hit at t=1ms is within FHCDT of guard -> still inhibited.
    # Normal hit at t=5ms is > FHCDT after the most recent hit (1ms+2ms < 5ms) -> opens event.
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2), make_hit(5e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert events[0].first_hit_channel == 2
    assert events[0].time == 5e-3


def test_combined_as_first_hit_inhibits():
    builder = EventBuilder(
        fhcdt=2e-3,
        dt1x_max=10e-3,
        dtnx_max=10e-3,
        channels={1: ChannelFunction.COMBINED, 2: ChannelFunction.NORMAL},
    )
    hits = [make_hit(0.0, 1), make_hit(5e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert events[0].first_hit_channel == 2


@pytest.mark.parametrize("func", [ChannelFunction.GUARD, ChannelFunction.COMBINED])
def test_guard_or_combined_as_subsequent_hit_is_included(func):
    builder = EventBuilder(
        fhcdt=0.5e-3,
        dt1x_max=10e-3,
        dtnx_max=10e-3,
        channels={1: ChannelFunction.NORMAL, 2: func},
    )
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert [h.channel for h in events[0].hits] == [1, 2]


def test_unused_channel_is_dropped():
    builder = EventBuilder(
        fhcdt=0.5e-3,
        dt1x_max=10e-3,
        dtnx_max=10e-3,
        channels={1: ChannelFunction.NORMAL, 2: ChannelFunction.UNUSED},
    )
    # Hit on channel 2 should be invisible -- no effect on event timing.
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2), make_hit(2e-3, 3)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert [h.channel for h in events[0].hits] == [1]


def test_channel_not_in_mapping_treated_as_unused():
    builder = EventBuilder(
        fhcdt=0.5e-3,
        dt1x_max=10e-3,
        dtnx_max=10e-3,
        channels={1: ChannelFunction.NORMAL},
    )
    hits = [make_hit(0.0, 1), make_hit(1e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert [h.channel for h in events[0].hits] == [1]


def test_channels_none_accepts_all_as_normal():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    hits = [make_hit(0.0, 5), make_hit(1e-3, 99)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert [h.channel for h in events[0].hits] == [5, 99]


def test_channels_iterable_form():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3, channels=[1, 2])
    hits = [make_hit(0.0, 1), make_hit(1e-3, 3), make_hit(2e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert [h.channel for h in events[0].hits] == [1, 2]


def test_a_flag_blocks_soe():
    builder = EventBuilder(fhcdt=2e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    # First hit has A-flag -> cannot be SoE.
    # Second hit (no flag) at 5ms is > FHCDT after the first -> becomes SoE.
    hits = [
        make_hit(0.0, 1, status=HitFlags.AFTER_TIMEOUT),
        make_hit(5e-3, 2),
    ]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert events[0].first_hit_channel == 2


def test_a_flag_allowed_as_subsequent_hit():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    hits = [
        make_hit(0.0, 1),
        make_hit(1e-3, 2, status=HitFlags.AFTER_TIMEOUT),
    ]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert [h.channel for h in events[0].hits] == [1, 2]


def test_flush_emits_open_event():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    assert builder.process(make_hit(0.0, 1)) == []
    closed = builder.flush()
    assert len(closed) == 1
    assert closed[0].close_reason == EventCloseReason.END_OF_STREAM


def test_flush_idempotent():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    builder.process(make_hit(0.0, 1))
    assert len(builder.flush()) == 1
    assert builder.flush() == []


def test_reset_after_flush():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    # Stream 1
    list(builder.process_all([make_hit(0.0, 1), make_hit(1e-3, 2)]))
    # Stream 2: starts fresh from t=0 again
    events = list(builder.process_all([make_hit(0.0, 1), make_hit(1e-3, 2)]))
    assert len(events) == 1
    assert events[0].time == 0.0
    assert len(events[0].hits) == 2


def test_out_of_order_raises():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    builder.process(make_hit(1.0, 1))
    with pytest.raises(ValueError, match="time-sorted"):
        builder.process(make_hit(0.5, 2))


def test_event_properties():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    hits = [make_hit(0.0, 3), make_hit(1e-3, 1), make_hit(2e-3, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    ev = events[0]
    assert ev.time == 0.0
    assert ev.first_hit_channel == 3
    assert ev.channel_sequence == [3, 1, 2]
    assert ev.dt_to_first == pytest.approx([1e-3, 2e-3])
    assert len(ev.hits) == 3


def test_event_single_hit_has_empty_dt_to_first():
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    events = list(builder.process_all([make_hit(0.0, 1)]))
    assert len(events) == 1
    assert events[0].dt_to_first == []
    assert events[0].channel_sequence == [1]


def test_identical_timestamps_join_same_event():
    # Equal timestamps are allowed (monotonicity check uses `<`); two simultaneous hits
    # on different channels should land in the same event.
    builder = EventBuilder(fhcdt=0.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    hits = [make_hit(0.0, 1), make_hit(0.0, 2)]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert [h.channel for h in events[0].hits] == [1, 2]


def test_duplicate_close_updates_fhcdt_reference():
    # The duplicate hit is excluded from events but its timestamp still resets the FHCDT
    # gap timer, so a subsequent hit within FHCDT of the duplicate cannot open a new event.
    builder = EventBuilder(fhcdt=3.5e-3, dt1x_max=10e-3, dtnx_max=10e-3)
    hits = [
        make_hit(0.0, 1),
        make_hit(1e-3, 2),
        make_hit(2e-3, 1),  # duplicate -> closes; FHCDT reference becomes 2 ms
        make_hit(5e-3, 3),  # gap from 2 ms is 3 ms <= fhcdt=3.5 ms -> inhibited
    ]
    events = list(builder.process_all(hits))
    assert len(events) == 1
    assert events[0].close_reason == EventCloseReason.DUPLICATE_CHANNEL
