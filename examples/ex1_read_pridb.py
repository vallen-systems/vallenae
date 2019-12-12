"""
Read pridb
==========
"""

#%%
import os
import matplotlib.pyplot as plt

import vallenae as vae

HERE = os.path.dirname(__file__) if "__file__" in locals() else os.getcwd()
PRIDB = os.path.join(HERE, "steel_plate/sample.pridb")

#%%
# Open pridb
# ----------
pridb = vae.io.PriDatabase(PRIDB)

print("Tables in database: ", pridb.tables())
print("Number of rows in data table (ae_data): ", pridb.rows())
print("Set of all channels: ", pridb.channel())

#%%
# Read hits to Pandas DataFrame
# -----------------------------
df_hits = pridb.read_hits()
# Print a few columns
df_hits[["time", "channel", "amplitude", "counts", "energy"]]

# %%
# Query Pandas DataFrame
# ----------------------
# DataFrames offer powerful features to query and aggregate data,
# e.g. plot summed energy per channel
ax = df_hits.groupby("channel").sum()["energy"].plot.bar(figsize=(8, 3))
ax.set_xlabel("Channel")
ax.set_ylabel("Summed Energy [eu = 1e-14 V²s]")
plt.tight_layout()

#%%
# Read markers
# ------------
df_markers = pridb.read_markers()
df_markers

#%%
# Read parametric data
# --------------------
df_parametric = pridb.read_parametric()
df_parametric
