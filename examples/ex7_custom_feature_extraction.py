"""
Custom feature extraction
=========================

Following examples shows how to compute custom features and save them in the transient feature
database (trfdb) to visualize them in VisualAE.

The feature extraction can be live during acquisition. VisualAE will be notified, that a writer to
the trfdb is active and waits for the features to be computed. Therefore, the computed features can
be visualized in real time.
"""

from pathlib import Path
from tempfile import gettempdir

import matplotlib.pyplot as plt
import numpy as np
import vallenae as vae

HERE = Path(__file__).parent if "__file__" in locals() else Path.cwd()
PRIDB = HERE / "bearing" / "bearing.pridb"
TRADB = HERE / "bearing" / "bearing_plain.tradb"
# TRFDB = HERE / "bearing" / "bearing.trfdb"
TRFDB_TMP = Path(gettempdir()) / "bearing_custom.trfdb"  # use a temp file for demo

#%%
# Custom feature extraction algorithms
# ------------------------------------
def rms(data: np.ndarray) -> float:
    """Root mean square (RMS)."""
    return np.sqrt(np.mean(data ** 2))


def crest_factor(data: np.ndarray) -> float:
    """Crest factor (ratio of peak amplitude and RMS)."""
    return np.max(np.abs(data)) / rms(data)


def spectral_peak_frequency(spectrum_: np.ndarray, samplerate: int) -> float:
    """
    Peak frequency in a spectrum.

    Args:
        spectrum: FFT amplitudes
        samplerate: Sample rate of the spectrum in Hz

    Returns:
        Peak frequency in Hz
    """
    def bin_to_hz(samplerate: int, samples: int, index: int):
        return 0.5 * samplerate * index / (samples - 1)

    peak_index = np.argmax(spectrum_)
    return bin_to_hz(samplerate, len(spectrum_), peak_index)

#%%
# Open tradb and trfdb
# --------------------
tradb = vae.io.TraDatabase(TRADB)
trfdb = vae.io.TrfDatabase(TRFDB_TMP, mode="rwc")

#%%
# Helper function to notify VisualAE, that the transient feature database is active/closed
def set_file_status(trfdb_: vae.io.TrfDatabase, status: int):
    """Notify VisualAE that trfdb is active/closed."""
    trfdb_.connection().execute(
        f"UPDATE trf_globalinfo SET Value = {status} WHERE Key == 'FileStatus'"
    )

#%%
# Read tra records, compute features and save to trfdb
# ----------------------------------------------------
# The `vallenae.io.TraDatabase.listen` method will read the tradb row by row and can be used during
# acquisition. Only if the acquisition is closed and no new records are available, the function
# returns.
set_file_status(trfdb, 2)  # 2 = active

for tra in tradb.listen(existing=True, wait=False):
    spectrum = np.fft.rfft(tra.data)
    features = vae.io.FeatureRecord(
        trai=tra.trai,
        features={
            "RMS": rms(tra.data),
            "CrestFactor": crest_factor(tra.data),
            "SpectralPeakFreq": spectral_peak_frequency(spectrum, tra.samplerate),
        }
    )
    trfdb.write(features)

set_file_status(trfdb, 0)  # 0 = closed

#%%
# Write field infos to trfdb
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Field infos can be written with `vallenae.io.TrfDatabase.write_fieldinfo`:
trfdb.write_fieldinfo("RMS", {"Unit": "[V]", "LongName": "Root mean square"})
trfdb.write_fieldinfo("CrestFactor", {"Unit": "[]", "LongName": "Crest factor"})
trfdb.write_fieldinfo("SpectralPeakFreq", {"Unit": "[Hz]", "LongName": "Spectral peak frequency"})

#%%
# Read results from trfdb
# -----------------------
df_trfdb = trfdb.read()
print(df_trfdb)

#%%
# Plot AE features and custom features
# ------------------------------------
# Read pridb and join it with trfdb:
with vae.io.PriDatabase(PRIDB) as pridb:
    df_pridb = pridb.read_hits()

df_combined = df_pridb.join(df_trfdb, on="trai", how="left")
print(df_combined)

#%%
# Plot joined features from pridb and trfdb
features = [
    # from pridb
    "amplitude",
    "energy",
    "counts",
    # from trfdb - custom
    "RMS",
    "CrestFactor",
    "SpectralPeakFreq",
]
df_combined.plot(
    x="time",
    y=features,
    xlabel="Time [s]",
    title=features,
    legend=False,
    subplots=True,
    figsize=(8, 10),
)
plt.suptitle("AE Features from pridb and custom features from trfdb")
plt.tight_layout()
plt.show()

#%%
# Display custom features in VisualAE
# -----------------------------------
#
# .. image:: /images/vae_custom_features.png
