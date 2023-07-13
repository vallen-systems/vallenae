"""
Spectrogram
===========

Generate spectrogram from tradb. The `vallenae.io.TraDatabase.read_continuous_wave` method is used
to read the transient data as a continuous array.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import vallenae as vae
from matplotlib.colors import LogNorm
from scipy import signal

HERE = Path(__file__).parent if "__file__" in locals() else Path.cwd()
TRADB = HERE / "bearing" / "bearing_plain.tradb"

#%%
# Read transient data as continous array
# --------------------------------------
# The signal is exactly cropped to the given time range (`time_start`, `time_stop`).
# Time gaps are filled with 0's.
with vae.io.TraDatabase(TRADB) as tradb:
    y, fs = tradb.read_continuous_wave(
        channel=1,
        time_start=None,
        time_stop=None,
        time_axis=False,  # return samplerate instead of time axis
        show_progress=False,
    )
    t = np.arange(0, len(y)) / fs  # generate time axis

#%%
# Compute Short-Time Fourier Transform (STFT)
# -------------------------------------------
nfft = 4096
noverlap = 2048
fz, tz, zxx = signal.stft(y, fs=fs, window="hann", nperseg=nfft, noverlap=noverlap)

#%%
# Plot time data and spectrogram
# ------------------------------
fig, ax = plt.subplots(
    nrows=2,
    sharex=True,
    figsize=(8, 6),
    tight_layout=True,
    gridspec_kw={"height_ratios": (1, 2)},
)
ax[0].plot(t, y * 1e3)
ax[0].set(xlabel="Time [s]", ylabel="Amplitude [mV]", title="Waveform")
ax[1].pcolormesh(tz, fz / 1e3, np.abs(zxx), norm=LogNorm())
ax[1].set(xlabel="Time [s]", ylabel="Frequency [kHz]", title="STFT")
plt.show()
