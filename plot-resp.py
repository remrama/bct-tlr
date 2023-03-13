"""Plot rrv somehow.
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

export_path = derivatives_dir / "rrv.png"


layout = BIDSLayout(bids_root, derivatives=True)

bids_files = layout.get(
    task="sleep",
    acquisition="nap",
    suffix="resp",
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

df = pd.concat(subject_dataframes)#.set_index(["participant_id", "cue", "location"])


# Average across all cues for each participant
df = df.groupby(["participant_id", "location"]).mean().drop(columns="cue")
# drop columns/measures that not all participants have
df = df.dropna(axis="columns")
# df = df.reset_index()


################################################################################
# PLOTTING
################################################################################


long_df = df.melt(ignore_index=False, var_name="measure")
plot_df = long_df.reset_index()

plot_measures = [
    # "RSP_Rate_Mean", 
    # "RRV_RMSSD",
    "RRV_MeanBB",
    "RRV_SDBB",
    # "RRV_SDSD",
    "RRV_CVBB",
    "RRV_CVSD",
    "RRV_MedianBB",
    "RRV_MadBB",
    "RRV_MCVBB",
    "RRV_LF",
    "RRV_HF",
    "RRV_LFHF",
    # "RRV_SD1",
    # "RRV_SD2",
    # "RRV_SD2SD1",
    # "RRV_ApEn",
    "RSP_Amplitude_Mean",
    "RSP_Symmetry_PeakTrough",
    # "RSP_Symmetry_RiseDecay",
    # "RSP_Phase_Duration_Inspiration",
    # "RSP_Phase_Duration_Expiration",
    # "RSP_Phase_Duration_Ratio",
]

g = sns.catplot(
    data=plot_df,
    x="location", order=["pre", "post"],
    col="measure", col_order=plot_measures,
    y="value",
    kind="point", height=2, aspect=0.6,
    errorbar="se",
    col_wrap=5,
    sharey=False,
)
g.set_titles("{col_name}")
utils.export_mpl(export_path)


desc = (df
    .groupby("location")
    .agg(["count", "min", "max", "median", "mean", "std", "sem"])
    .stack(0)
    .rename_axis(["location", "measure"])
    .sort_index(level="location", ascending=False)
)


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



meas = "RSP_Rate_Mean"

pre = df.loc[(slice(None), "pre"), meas]
post = df.loc[(slice(None), "post"), meas]
ttest = pg.ttest(pre, post, paired=True)
wilcoxon = pg.wilcoxon(pre, post)


xvals = [0, 1]
### CHANGE slice to specifically ["pre", "post"]
yvals = desc.loc[(slice(None), meas), "mean"].to_numpy()
yerrs = desc.loc[(slice(None), meas), "sem"].to_numpy()
bars = ax.bar(xvals, yvals, yerr=yerrs, **bar_kwargs)
bars.errorbar.lines[2][0].set_capstyle("round")

ax.set_xticks(xvals)
ax.set_xticklabels(["Pre-cue", "Post-cue"])
ax.margins(x=0.2)
# ax.set_ylim(0, 1)
# ax.yaxis.set_major_locator(plt.MultipleLocator(0.5))
# ax.yaxis.set_minor_locator(plt.MultipleLocator(0.1))

# Draw paired participant lines.
temp = df[meas].unstack()[["pre", "post"]]
jitter = 0.05
participant_palette = utils.load_participant_palette()
colors = temp.index.map(participant_palette).to_numpy()
segments = [ np.column_stack([xvals, row]) for row in temp.to_numpy() ]
np.random.seed(1)
for seg in segments:
    # seg[:, 0] += np.random.normal(loc=0, scale=jitter)
    seg[:, 0] += np.random.uniform(-jitter, jitter)
lines = LineCollection(
    segments,
    colors=colors,
    label=temp.index.to_numpy(),
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

# ax.set_ybound(lower=30)
ax.set_ylabel("Respiration rate")
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(which="both", top=False, right=False, bottom=False)
ax.grid(False)

export_path = export_path.with_name(f"rrv-{meas}")
utils.export_mpl(export_path)
