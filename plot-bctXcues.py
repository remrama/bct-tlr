"""Plot all BCT presses of all participants.
"""
from bids import BIDSLayout
from matplotlib.collections import LineCollection
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import pingouin as pg

import utils


utils.set_matplotlib_style()


bids_root = utils.ROOT_DIR
derivatives_dir = utils.DERIVATIVES_DIR

export_path = derivatives_dir / "task-bctXcues.png"


layout = BIDSLayout(bids_root)

bids_files = layout.get(
    task="bct",
    acquisition=["pre", "post"],
    suffix="beh",
    extension=".tsv",
)

# Stack all participants into one dataframe.
subject_dataframes = []
for bf in bids_files:
    participant_id = "sub-" + bf.entities["subject"]
    acquisition_id = "acq-" + bf.entities["acquisition"]
    sub_df = bf.get_df(
        ).assign(participant_id=participant_id, acquisition_id=acquisition_id
        ).set_index(["participant_id", "acquisition_id"])
    subject_dataframes.append(sub_df)

df = pd.concat(subject_dataframes)

df["rt_diff"] = (df
    .groupby(["participant_id", "acquisition_id", "cycle"])
    ["timestamp"].diff()
)
desc = (df
    .groupby(["participant_id", "acquisition_id", "cycle"])
    .agg({"accuracy": ["count", "last"], "rt_diff": ["mean", "std"]})
)
desc.columns = ["n", "accuracy", "rt_mean", "rt_std"]

accuracy = desc["accuracy"].eq("correct").groupby(["participant_id", "acquisition_id"]).mean()

acc = accuracy.to_frame().reset_index()
table = acc.pivot(index="participant_id", columns="acquisition_id", values="accuracy")
table = table.dropna().rename_axis(columns=None).sort_index(axis=1, ascending=False)
table["diff"] = table["acq-post"].sub(table["acq-pre"])
table_desc = table.describe().T.join(table.sem().rename("sem"))


layout2 = BIDSLayout(bids_root, derivatives=True)
bids_files2 = layout2.get(
    task="sleep",
    acquisition="nap",
    suffix="cues",
    extension=".tsv",
)

# Stack all participants into one dataframe.
subject_dataframes2 = []
for bf in bids_files2:
    participant_id = "sub-" + bf.entities["subject"]
    acquisition_id = "acq-" + bf.entities["acquisition"]
    sub_df = bf.get_df(
        ).assign(participant_id=participant_id, acquisition_id=acquisition_id
        ).set_index(["participant_id", "acquisition_id"])
    subject_dataframes2.append(sub_df)
df2 = pd.concat(subject_dataframes2)

n_cues = df2.groupby("participant_id")["frequency"].sum().rename("n_cues")

dat = table.join(n_cues, how="outer")
dat = dat.dropna()

x = dat["n_cues"].to_numpy()
y = dat["diff"].to_numpy()

corr = pg.corr(x, y, method="pearson")


################################################################################
# PLOTTING
################################################################################


participant_palette = utils.load_participant_palette()
colors = dat.index.map(participant_palette).to_numpy()

# Get regression line predictor.
coef = np.polyfit(x, y, 1)
poly1d_func = np.poly1d(coef)

# Open figure.
fig, ax = plt.subplots(figsize=(2, 2))

# Draw dots and regression line.
ax.plot(x, poly1d_func(x), "-k")
# ax.plot(x, y, "ko", ms=8, alpha=0.8, mec="white", mew=0.5)
ax.scatter(x, y, marker="o", c=colors, s=80, alpha=1, edgecolor="white", linewidth=0.5)

# Aesthetics.
ax.set_xlabel("Number of nap cues")
# ax.set_ylabel(r"$\Delta$ BCT accuracy" + "\n" + r"worse$\leftarrow$   $\rightarrow$better")
ax.set_ylabel(r"$\Delta$ BCT accuracy")

# ax.set_xlim(*control_limits)
# ax.set_ylim(*emotion_limits)
# ax.xaxis.set_major_locator(plt.MultipleLocator(1))
# ax.yaxis.set_major_locator(plt.MultipleLocator(10))
ax.grid(False, axis="both")
ax.margins(0.2)
# ax.set_aspect(1)

r, p = corr.loc["pearson", ["r", "p-val"]]
pcolor ="black" if p < 0.1 else "gainsboro"
if p < 0.05:
    ptext = "*" * sum([ p<cutoff for cutoff in (0.05, 0.01, 0.001) ])
else:
    ptext = fr"$p={p:.2f}$".replace("0", "", 1)
rtext = fr"$r={r:.2f}$".replace("0.", ".")
text = "\n".join([rtext, ptext])
ax.text(
    0.4,
    0.9,
    text,
    color=pcolor,
    transform=ax.transAxes,
    ha="right",
    va="top",
)


utils.export_mpl(export_path)

