"""
Event Builder
=============

Group time-sorted hits into acoustic-emission events with ``vallenae.processor.EventBuilder``.

The Event Builder is a streaming state machine that mirrors VisualAE's grouping logic.
It assigns hits to events using three timing parameters:

- **FHCDT** -- First Hit Channel Discrimination Time. Quiet gap required before a hit qualifies
  as Start-of-Event (SoE).
- **DT1X-Max** -- maximum time between SoE and any hit in the event.
- **DTNX-Max** -- maximum time between two consecutive hits in the event.

This example feeds the hits from ``steel_plate/sample.pridb`` into the builder using the same
parameters as the bundled ``sample.vaex`` setup.
"""

# %%
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import vallenae as vae

HERE = Path(__file__).parent if "__file__" in locals() else Path.cwd()
PRIDB = HERE / "steel_plate" / "sample.pridb"
TRADB = HERE / "steel_plate" / "sample.tradb"

# %%
# Stream hits into the Event Builder
# ----------------------------------
# ``EventBuilder.process_all`` consumes any iterable of ``HitRecord``'s and yields ``Event``'s as
# they close. We feed it directly from ``iread_hits`` -- no need to materialize a DataFrame.
builder = vae.processor.EventBuilder(fhcdt=2e-3, dt1x_max=2e-3, dtnx_max=2e-3)
with vae.io.PriDatabase(PRIDB) as pridb:
    events = list(builder.process_all(pridb.iread_hits()))

print(f"{len(events)} event(s) built from {sum(len(ev.hits) for ev in events)} hit(s)")

# %%
# Inspect the resulting events
# ----------------------------
# Each ``Event`` exposes its hits time-sorted, the first-hit channel, the channel sequence, and
# the time deltas of the subsequent hits to the SoE (VisualAE's DT12..DT1n).
for i, ev in enumerate(events, start=1):
    print(f"Event {i}: SoE at t = {ev.time:.6f} s, close reason = {ev.close_reason.name}")
    print(f"  channel sequence: {ev.channel_sequence}")
    print(f"  dt to first hit:  {[f'{dt * 1e6:.1f} µs' for dt in ev.dt_to_first]}")

# Pick the (only) event in this sample and pre-compute arrival times relative to the SoE.
event = events[0]
arrival_us = np.array([0.0, *event.dt_to_first]) * 1e6

# %%
# Delta-time matrix
# -----------------
# Pairwise arrival-time differences between every channel pair in the event, in µs.
# Cell (i, j) is the delay from channel i to channel j (positive = j arrived later).
# This is the input most acoustic-emission localization algorithms work with.
df_dt = pd.DataFrame(
    arrival_us[None, :] - arrival_us[:, None],
    index=pd.Index(event.channel_sequence, name="ch"),
    columns=event.channel_sequence,
)
print(df_dt.round(2))

# %%
# Visualize the event
# -------------------
# Plot the waveform of every hit in the event on its own row, aligned on the Start-of-Event.
# The vertical dashed lines mark each hit's arrival time -- you can see the AE wavefront
# reaching the four sensors a few µs apart, which is exactly what the Event Builder grouped.
window_us = (-20, 250)
fig, axes = plt.subplots(
    nrows=len(event.hits),
    sharex=True,
    sharey=True,
    figsize=(8, 1.4 * len(event.hits) + 0.6),
    tight_layout=True,
)
fig.suptitle(
    f"Event with {len(event.hits)} hits "
    f"(channel sequence {event.channel_sequence}, SoE at t = {event.time:.4f} s)"
)
axes[-1].set_xlabel("Time relative to SoE [µs]")

with vae.io.TraDatabase(TRADB) as tradb:
    for ax, hit, dt_us in zip(axes, event.hits, arrival_us):
        y, t = tradb.read_wave(hit.trai)
        t_us = t * 1e6 + dt_us
        mask = (t_us >= window_us[0]) & (t_us <= window_us[1])
        ax.plot(t_us[mask], y[mask] * 1e3, color="C0", linewidth=0.8)
        ax.axvline(dt_us, color="C3", linestyle="--")
        ax.set_ylabel(f"Ch {hit.channel} [mV]")

plt.show()
