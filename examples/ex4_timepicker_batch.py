"""
Timepicker batch processing
===========================

Following examples shows how to stream transient data row by row,
compute timepicker results and save the results to a feature database (trfdb).
"""

from pathlib import Path
from shutil import copyfile
from tempfile import gettempdir

import matplotlib.pyplot as plt
import pandas as pd
import vallenae as vae

HERE = Path(__file__).parent if "__file__" in locals() else Path.cwd()
TRADB = HERE / "steel_plate" / "sample_plain.tradb"
TRFDB = HERE / "steel_plate" / "sample.trfdb"
TRFDB_TMP = Path(gettempdir()) / "sample.trfdb"

#%%
# Open tradb (readonly) and trfdb (readwrite)
# -------------------------------------------
copyfile(TRFDB, TRFDB_TMP)  # copy trfdb, so we don't overwrite it

tradb = vae.io.TraDatabase(TRADB)
trfdb = vae.io.TrfDatabase(TRFDB_TMP, mode="rw")  # allow writing

#%%
# Read current trfdb
# ------------------
print(trfdb.read())

#%%
# Compute arrival time offsets with different timepickers
# -------------------------------------------------------
# To improve localisation, time of arrival estimates
# using the first threshold crossing can be refined with timepickers.
# Therefore, arrival time offsets between the first threshold crossings
# and the timepicker results are computed.
def dt_from_timepicker(timepicker_func, tra: vae.io.TraRecord):
    # Index of the first threshold crossing is equal to the pretrigger samples
    index_ref = tra.pretrigger
    # Only analyse signal until peak amplitude
    index_peak = vae.features.peak_amplitude_index(tra.data)
    data = tra.data[:index_peak]
    # Get timepicker result
    _, index_timepicker = timepicker_func(data)
    # Compute offset in µs
    return (index_timepicker - index_ref) * 1e6 / tra.samplerate

#%%
# Transient data is streamed from the database row by row using `vallenae.io.TraDatabase.iread`.
# Only one transient data set is loaded into memory at a time.
# That makes the streaming interface ideal for batch processing.
# The timepicker results are saved to the trfdb using `vallenae.io.TrfDatabase.write`.

for tra in tradb.iread():
    # Calculate arrival time offsets with different timepickers
    feature_set = vae.io.FeatureRecord(
        trai=tra.trai,
        features={
            "ATO_Hinkley": dt_from_timepicker(vae.timepicker.hinkley, tra),
            "ATO_AIC": dt_from_timepicker(vae.timepicker.aic, tra),
            "ATO_ER": dt_from_timepicker(vae.timepicker.energy_ratio, tra),
            "ATO_MER": dt_from_timepicker(vae.timepicker.modified_energy_ratio, tra),
        }
    )
    # Save results to trfdb
    trfdb.write(feature_set)

#%%
# Read results from trfdb
# -----------------------
print(trfdb.read().filter(regex="ATO"))

#%%
# Plot results
# ------------
ax = trfdb.read()[["ATO_Hinkley", "ATO_AIC", "ATO_ER", "ATO_MER"]].plot.barh()
ax.invert_yaxis()
ax.set_xlabel("Arrival time offset [µs]")
plt.show()

#%%
# Plot waveforms and arrival times
# --------------------------------
_, axes = plt.subplots(4, 1, tight_layout=True, figsize=(8, 8))
for row, ax in zip(trfdb.read().itertuples(), axes):
    trai = row.Index

    # read waveform from tradb
    y, t = tradb.read_wave(trai)

    # plot waveform
    ax.plot(t[400:1000] * 1e6, y[400:1000] * 1e3, "k")  # crop and convert to µs/mV
    ax.set_title(f"trai = {trai}")
    ax.set_xlabel("Time [µs]")
    ax.set_ylabel("Amplitude [mV]")
    ax.label_outer()
    # plot arrival time offsets
    ax.axvline(row.ATO_Hinkley, color="C0")
    ax.axvline(row.ATO_AIC, color="C1")
    ax.axvline(row.ATO_ER, color="C2")
    ax.axvline(row.ATO_MER, color="C3")

axes[0].legend(["Waveform", "Hinkley", "AIC", "ER", "MER"])
plt.show()

#%%
# Use results in VisualAE
# -----------------------
# The computed arrival time offsets can be directly used in VisualAE.
# We only need to specify the unit. VisualAE requires them to be in µs.
# Units and other column-related meta data is saved in the `trf_fieldinfo` table.
# Field infos can be retrieved with `vallenae.io.TrfDatabase.fieldinfo`:
print(trfdb.fieldinfo())

#%%
# Show results as table:
print(pd.DataFrame(trfdb.fieldinfo()))

#%%
# Write units to trfdb
# ~~~~~~~~~~~~~~~~~~~~
# Field infos can be written with `vallenae.io.TrfDatabase.write_fieldinfo`:

trfdb.write_fieldinfo("ATO_Hinkley", {"Unit": "[µs]", "LongName": "Arrival Time Offset (Hinkley)"})
trfdb.write_fieldinfo("ATO_AIC", {"Unit": "[µs]", "LongName": "Arrival Time Offset (AIC)"})
trfdb.write_fieldinfo("ATO_ER", {"Unit": "[µs]", "LongName": "Arrival Time Offset (ER)"})
trfdb.write_fieldinfo("ATO_MER", {"Unit": "[µs]", "LongName": "Arrival Time Offset (MER)"})

print(pd.DataFrame(trfdb.fieldinfo()).filter(regex="ATO"))


#%%
# Load results in VisualAE
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Time arrival offsets can be specified in the settings of `Location Processors` - `Channel Positions` - `Arrival Time Offset`.
# (Make sure to rename the generated trfdb to match the filename of the pridb.)
#
# .. image:: /images/vae_arrival_time_offset.png
