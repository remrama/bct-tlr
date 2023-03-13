"""Plot all BCT presses of all participants.
"""
from bids import BIDSLayout
from matplotlib.collections import LineCollection
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pingouin as pg

import utils


bids_root = utils.ROOT_DIR
derivatives_dir = utils.DERIVATIVES_DIR

export_path = derivatives_dir / "task-bct.png"


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
table = table.dropna()

acc_desc = table.describe().T.join(table.sem().rename("sem"))


pre, post = table[["acq-pre", "acq-post"]].T.to_numpy()
ttest = pg.ttest(pre, post, paired=True)
wilcoxon = pg.wilcoxon(pre, post)


figsize = (2, 3)

bar_kwargs = {
    "width": 0.8,
    "color": "white",
    "edgecolor": "black",
    "linewidth": 1,
    "zorder": 1,
    "error_kw": dict(capsize=3, capthick=1, ecolor="black", elinewidth=1, zorder=2),
}

lines_kwargs = {"linewidths": 0.5, "zorder": 3}

scatter_kwargs = {
    "s": 30,
    "linewidths": 0.5,
    "edgecolors": "white",
    "clip_on": False,
    "zorder": 4,
}

utils.set_matplotlib_style()
fig, ax = plt.subplots(figsize=figsize)

xvals = [0, 1]
yvals = acc_desc.loc[["acq-pre", "acq-post"], "mean"].to_numpy()
yerrs = acc_desc.loc[["acq-pre", "acq-post"], "sem"].to_numpy()
bars = ax.bar(xvals, yvals, yerr=yerrs, **bar_kwargs)
bars.errorbar.lines[2][0].set_capstyle("round")

ax.set_xticks(xvals)
ax.set_xticklabels(["Pre-nap", "Post-nap"])
ax.margins(x=0.2)
ax.set_ylim(0, 1)
ax.yaxis.set_major_locator(plt.MultipleLocator(0.5))
ax.yaxis.set_minor_locator(plt.MultipleLocator(0.1))

# Draw paired participant lines.
jitter = 0.05
participant_palette = utils.load_participant_palette()
colors = table.index.map(participant_palette).to_numpy()
segments = [ np.column_stack([xvals, row]) for row in table[["acq-pre", "acq-post"]].to_numpy() ]
np.random.seed(1)
for seg in segments:
    # seg[:, 0] += np.random.normal(loc=0, scale=jitter)
    seg[:, 0] += np.random.uniform(-jitter, jitter)
lines = LineCollection(
    segments,
    colors=colors,
    label=table.index.to_numpy(),
    # offsets=offsets, offset_transform=None,
    **lines_kwargs,
)
ax.add_collection(lines)

scatterx, scattery = np.row_stack(segments).T
scatterc = np.repeat(colors, 2)
ax.scatter(scatterx, scattery, c=scatterc, **scatter_kwargs)

p = wilcoxon.at["Wilcoxon", "p-val"]
pcolor ="black" if p < 0.1 else "gainsboro"
ax.hlines(
    y=1.05,
    xmin=xvals[0],
    xmax=xvals[1],
    linewidth=0.5,
    color=pcolor,
    capstyle="round",
    transform=ax.get_xaxis_transform(),
    clip_on=False,
)
if p < 0.05:
    ptext = "*" * sum([ p<cutoff for cutoff in (0.05, 0.01, 0.001) ])
else:
    ptext = fr"$p={p:.2f}$".replace("0", "", 1)

ax.text(0.5, 1.05, ptext,
    color=pcolor,
    transform=ax.transAxes,
    ha="center",
    va="bottom",
)

ax.set_ylabel("BCT accuracy")
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(which="both", top=False, right=False, bottom=False)
ax.grid(False)


utils.export_mpl(export_path)

# for p, p_df in df.groupby("participant_id"):
#     c = participant_palette[p]
#     data = p_df.set_index(["intervention", "acquisition_id"]
#         ).reindex(index=ordered_indx
#         )["empathic_accuracy"].values
#     jittered_xvals = xvals + np.random.normal(loc=0, scale=SUBJ_JITTER)
#     ax.plot(jittered_xvals, data, "-o", color=c, **PLOT_KWARGS)


# cycle_accuracy = (df
#     ["accuracy"].last()
# )

# accuracy = (cycle_accuracy
#     .eq("correct")
#     .groupby(["participant_id", "acquisition_id"])
#     .agg(["count", "mean"])
# )

# utils.export_tsv(df, export_path, index=False)

