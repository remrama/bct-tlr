"""lucidity."""
import argparse
from pathlib import Path

from bids import BIDSLayout
import numpy as np
import pandas as pd
import pingouin as pg

import matplotlib.pyplot as plt

import utils

utils.set_matplotlib_style()


plt.rcParams["savefig.dpi"] = 1000
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = "Arial"

export_path = utils.DERIVATIVES_DIR / "lucidity.png"
export_path_table = utils.DERIVATIVES_DIR / "lucidity.tsv"

layout = BIDSLayout(utils.ROOT_DIR, validate=False)

bids_files = layout.get(
    task="sleep",
    suffix="rep",
    extension=".tsv",
)

# Stack all participants into one dataframe.
subject_dataframes = []
for bf in bids_files:
    ### THIS IS USED A LOT, SHOULD BE UTILITY (loading and adding subject or other entities to df)
    participant_id = "sub-" + bf.entities["subject"]
    acquisition_id = "acq-" + bf.entities["acquisition"]
    sub_df = bf.get_df().assign(participant_id=participant_id)
    subject_dataframes.append(sub_df)
df = pd.concat(subject_dataframes).set_index(["participant_id", "awakening_id"])

# drop subject 906, too early
df = df.drop("sub-906")
# drop subjects who did naps
df = df.drop("sub-907")

# Drop any awakenings without dreams.
df = df.query("Recall.eq(2)")


ser = df.groupby("participant_id")["Lucidity"].max().ge(3).rename("had_lucid")
utils.export_tsv(ser, export_path_table)

x = ser.to_numpy()
ci, dist = pg.compute_bootci(x, func="mean", method="cper", n_boot=2000, return_dist=True)

ci *= 100
dist *= 100

fig, ax = plt.subplots(figsize=(1.7, 2))
ax.axhline(50, color="black", lw=0.5, ls="dashed", zorder=0)
# ax.text(0.7, 50, "Carr et al., 2020", ha="left", va="bottom", transform=ax.get_yaxis_transform())
box = ax.boxplot(dist,
    showmeans=True,
    boxprops=dict(
        linestyle="-",
        linewidth=1,
        color="black",
    ),
    medianprops=dict(
        linestyle="--",
        linewidth=1,
        color="black",
    ),
    meanprops=dict(
        marker="o",
        markerfacecolor="black",
        markeredgecolor="white",
    ),
    flierprops=dict(
        marker="o",
        markerfacecolor="green",
        markersize=12,
        markeredgecolor="none",
    ),
    meanline=False,
    notch=True, bootstrap=10000,
    showfliers=False,
    showcaps=False,
    patch_artist=True,
    zorder=10,
)

for patch in box["boxes"]:
    patch.set_facecolor("white")

ax.set_ylabel(r"% of participants who became lucid")
ax.tick_params(direction="out", which="both", right=False, top=False, bottom=False, labelbottom=False)
ax.yaxis.set_major_locator(plt.MultipleLocator(50))
ax.yaxis.set_minor_locator(plt.MultipleLocator(10))
ax.spines[["top", "right", "bottom"]].set_visible(False)
ax.grid(False)
# ax.set_ylim(0, 100)


utils.export_mpl(export_path)
