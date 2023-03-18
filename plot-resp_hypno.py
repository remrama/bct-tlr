"""Plot hypnogram(s) for a single subject. Might be two hypnos in one."""

import argparse

from bids import BIDSLayout
import colorcet as cc
import matplotlib.pyplot as plt
import numpy as np
# import pandas as pd
import yasa

import utils

utils.set_matplotlib_style()

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--participant", type=int, required=True)
parser.add_argument("-c", "--channel", type=str, default="RESP", choices=["RESP", "Airflow"])
args = parser.parse_args()

participant = args.participant
resp_ch = args.channel



layout = BIDSLayout(utils.ROOT_DIR, derivatives=True, validate=False)
# stimuli_dir = bids_root / "stimuli"
bids_files = layout.get(
    subject=f"{participant:03d}",
    task="sleep",
    acquisition="nap",
    suffix=["hypno", "events", "resp"],
    extension=".tsv",
    # return_type="filename",
)

for bf in bids_files:
    if bf.entities["suffix"] == "hypno":
        hypno = bf.get_df()
    elif bf.entities["suffix"] == "events":
        events = bf.get_df()
    elif bf.entities["suffix"] == "resp":
        resp = bf.get_df()


def cmap2hex(cmap, n_intervals) -> list:
    if isinstance(cmap, str):
        if (cmap := cc.cm.get(cmap)) is None:
            try:
                cmap = plt.get_cmap(cmap)
            except ValueError as e:
                raise e
    assert isinstance(cmap, plt.matplotlib.colors.LinearSegmentedColormap)
    stops = [ 0 + x*1/(n_intervals-1) for x in range(n_intervals) ] # np.linspace
    hex_codes = []
    for s in stops:
        assert isinstance(s, float)
        rgb_floats = cmap(s)
        rgb_ints = [ round(f*255) for f in rgb_floats ]
        hex_code = "#{0:02x}{1:02x}{2:02x}".format(*rgb_ints)
        hex_codes.append(hex_code)
    return hex_codes

# Open figure.
# Hypnogram and Cues
# Hypnogram probabilities
# Respiration
fig, axes = plt.subplots(
    nrows=3,
    figsize=(6, 4),
    sharex=True, sharey=False,
    gridspec_kw=dict(height_ratios=[1, 1, 1]),
)

ax_hypno = axes[0]
ax_probas = axes[1]
ax_resp = axes[2]

#####################################
# HYPNOGRAM
#####################################

# Convert hypnogram stages to ints to ensure proper order.
stage_order = ["N3", "N2", "N1", "R", "W"]
stage_labels = ["SWS", "N2", "N1", "REM", "Wake"]
n_stages = len(stage_order)

hypno_int = hypno["description"].map(stage_order.index).to_numpy()
hypno_secs = hypno["duration"].mul(hypno["epoch"]).to_numpy()
hypno_hrs = hypno_secs / 60 / 60
hypno_rem = np.ma.masked_not_equal(hypno_int, stage_order.index("R"))

step_kwargs = dict(color="black", linewidth=0.5, linestyle="solid")
ax_hypno.step(hypno_hrs, hypno_int, **step_kwargs)


########################################
# CUE EVENTS
########################################

events = events.query("description.eq('Cue')")
onsets = events["onset"].div(60).div(60).to_numpy()
durations = events["duration"].div(60).div(60).to_numpy()
xranges = [(o, d) for o, d in zip(onsets, durations)]  # xmin, xwidth
yrange = (n_stages - 1, 1)  # ymin, yheight
ax_hypno.broken_barh(xranges, yrange, facecolors="mediumpurple", alpha=0.9)

ax_hypno.set_yticks(range(n_stages))
ax_hypno.set_yticklabels(stage_labels)
ax_hypno.set_ylabel("Sleep Stage")
ax_hypno.spines[["top", "right"]].set_visible(False)
ax_hypno.tick_params(axis="both", direction="out", top=False, right=False)
ax_hypno.set_ybound(upper=n_stages)

ax_hypno.text(1, 1,
    "Mindfulness audio cues",
    color="mediumpurple",
    ha="right", va="bottom",
    transform=ax_hypno.transAxes,
)



########################################
# HYPNOGRAM PROBABILITIES
########################################

probas = hypno[["proba_N1", "proba_N2", "proba_N3", "proba_R", "proba_W"]].T.to_numpy()
blues = cmap2hex("blues", 4)[1:]
colors = blues + ["indianred", "gray"]
ax_probas.stackplot(hypno_hrs, probas, colors=colors, alpha=0.9)
ax_probas.set_ylabel("Sleep Stage")

ax_probas.set_ylabel("Sleep Stage\nProbability")
ax_probas.tick_params(axis="both", which="both", direction="out", top=False, right=False)
ax_probas.set_ylim(0, 1)
ax_probas.yaxis.set_major_locator(plt.MultipleLocator(1))
ax_probas.yaxis.set_minor_locator(plt.MultipleLocator(1/n_stages))
ax_probas.grid(which="minor")


########################################
# RESPIRATION
########################################

resp = resp.query(f"channel=='{resp_ch}'").drop(columns="channel")
resp = resp.rolling(6000, center=True).mean().dropna()
time_hrs = resp["time"].div(60).div(60).to_numpy()
rrate = resp["RSP_Rate"].to_numpy()
rrv = resp["RSP_RVT"].to_numpy()
plot_kwargs = dict(linewidth=0.5, linestyle="solid")
ax_twin = ax_resp.twinx()
ax_resp.plot(time_hrs, rrate, color="black", **plot_kwargs)
ax_twin.plot(time_hrs, rrv, color="green", **plot_kwargs)
ax_resp.set_ylabel("Respiration Rate")
ax_twin.set_ylabel("RR Variability", rotation=270, va="bottom", color="green")

ax_resp.tick_params(axis="both", which="both", direction="out", top=False, right=False)
ax_resp.set_xbound(lower=0, upper=hypno_hrs.max())
ax_resp.set_xlabel("Time (hours)")
ax_resp.grid(False)
ax_twin.grid(False)


########################################
# AESTHETICS
########################################


legend_labels = ["Awake", "REM", "N1", "N2", "N3"]
legend_colors = ["gray", "indianred"] + blues
handles = [ plt.matplotlib.patches.Patch(label=l, facecolor=c,
        edgecolor="black", linewidth=.5)
    for l, c in zip(legend_labels, legend_colors) ]
legend = ax_probas.legend(
    handles=handles,
    loc="upper left", bbox_to_anchor=(1, 1),
    # handlelength=1, handleheight=.3,
    # handletextpad=,
    borderaxespad=0,
    labelspacing=.01,
    # columnspacing=,
    ncol=1, fontsize=6,
)

fig.align_ylabels()


export_pattern = "derivatives/sub-{subject}/sub-{subject}_task-{task}_acq-{acquisition}_resp.png"
export_path = layout.build_path(bf.entities, export_pattern, validate=False)
utils.export_mpl(export_path)
