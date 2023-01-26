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
parser.add_argument("--participant", type=int, default=4)
# parser.add_argument("--proba", action="store_true", help="Plot underlying probability estimates of all stages.")
# parser.add_argument("--cues", action="store_true", help="Overlay timestamped cues")
args = parser.parse_args()

participant = args.participant


layout = BIDSLayout(utils.ROOT_DIR, derivatives=True, validate=False)
# stimuli_dir = bids_root / "stimuli"
bids_files = layout.get(subject=f"{participant:03d}",
    task="sleep",
    acquisition="overnight",
    # suffix="hypno",
    extension=".tsv",
    # return_type="filename",
)

for bf in bids_files:
    if bf.entities["suffix"] == "hypno":
        hypno = bf.get_df()
    elif bf.entities["suffix"] == "events":
        events = bf.get_df()


# hypnogram_int = hypnogram_events["value"]
# assert hypnogram_events["duration"].nunique() == 1
# epoch_length = hypnogram_events["duration"].unique()[0]
# sampling_frequency = 1 / epoch_length

# stimuli_dir = bids_root / "stimuli"
# participant_id = f"sub-{participant_number:03d}"

# import_path_events = bids_root / participant_id / f"{participant_id}_task-sleep_events.tsv"
# import_path_hypno = bids_root / "derivatives" / participant_id / f"{participant_id}_task-sleep_hypno.tsv"
# export_path_plot = bids_root / "derivatives" / participant_id / f"{participant_id}_task-sleep_hypno.png"
# export_path_plot.parent.mkdir(parents=True, exist_ok=True)

# hypno = pd.read_csv(import_path_hypno, sep="\t")
# events = pd.read_csv(import_path_events, sep="\t")


# Convert hypnogram stages to ints to ensure proper order.
stage_order = ["N3", "N2", "N1", "R", "W"]
stage_labels = ["SWS", "N2", "N1", "REM", "Wake"]
n_stages = len(stage_order)

hypno_int = hypno["description"].map(stage_order.index).to_numpy()
hypno_secs = hypno["duration"].mul(hypno["epoch"]).to_numpy()
hypno_hrs = hypno_secs / 60 / 60

hypno_rem = np.ma.masked_not_equal(hypno_int, stage_order.index("R"))


figsize = (5, 2)
fig, (ax0, ax1) = plt.subplots(nrows=2, figsize=figsize,
    sharex=True, sharey=False, gridspec_kw={"height_ratios": [2, 1]})

step_kwargs = dict(color="black", linewidth=.5, linestyle="solid")

### Normal hypnogram
ax0.step(hypno_hrs, hypno_int, **step_kwargs)

# proba.plot(kind="area", color=palette, figsize=(10, 5), alpha=0.8, stacked=True, lw=0)

palette = {
    "bct": "orchid",
    "DreamReport": "gold",
    "lrlr": "forestgreen",
}

try:
    ev = events.query("description.isin(['DreamReport', 'Cue'])")
    # ev.loc[ev["description"].eq("DreamReport"), "onset"]

    lrlr_onset = 7766 / 60 / 60
    lrlr_duration = 2 / 60 / 60
    # lrlr_duration = 0.02

    # Move dream report from description into trial_type so it's in the same place as bct and tasks.
    ev["trial_type"] = ev["trial_type"].fillna(ev["description"])
    onsets = ev["onset"].div(60).div(60).to_numpy()
    widths = ev["duration"].div(60).div(60).to_numpy()
    # labels = ev["trial_type"].to_numpy()
    colors = ev["trial_type"].map(palette).to_numpy()

    onsets = np.append(lrlr_onset, onsets)
    widths = np.append(lrlr_duration, widths)
    colors = np.append(palette["lrlr"], colors)

    xranges = [ (x, w) for x, w in zip(onsets, widths) ]  # xmin, xwidth
    yrange = (n_stages - 0.5, 0.5)  # ymin, yheight

    # ax0.broken_barh(xranges, yrange, facecolors=colors)
    # ax0.eventplot(positions=cue_hrs, orienteation="horizontal",
    #     lineoffsets=n_stages-.5, linelengths=1, linewidths=.1,
    #     colors="mediumpurple", linestyles="solid")

    # ax0.text(0, 1, "Deep breathing cues", color="mediumpurple",
    #     ha="left", va="bottom", transform=ax0.transAxes)
except:
    pass

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

## Probabilities
probas = hypno[["proba_N1", "proba_N2", "proba_N3", "proba_R", "proba_W"]].T.to_numpy()
blues = cmap2hex("blues", 4)[1:]
colors = blues + ["indianred", "gray"]
ax1.stackplot(hypno_hrs, probas, colors=colors, alpha=.9)

ax0.set_yticks(range(n_stages))
ax0.set_yticklabels(stage_labels)
ax0.set_ylabel("Sleep Stage")
ax0.spines[["top", "right"]].set_visible(False)
ax0.tick_params(axis="both", direction="out", top=False, right=False)
ax0.set_ybound(upper=n_stages)
ax0.set_xbound(lower=0, upper=hypno_hrs.max())

ax1.set_ylabel("Sleep Stage\nProbability")
ax1.set_xlabel("Time (hours)")
ax1.tick_params(axis="both", which="both", direction="out", top=False, right=False)
ax1.set_ylim(0, 1)
ax1.yaxis.set_major_locator(plt.MultipleLocator(1))
ax1.yaxis.set_minor_locator(plt.MultipleLocator(1/n_stages))
ax1.grid(which="minor")

# Legends. (need 2, one for the button press type and one for accuracy)
legend_labels = ["Awake", "REM", "N1", "N2", "N3"]
legend_colors = ["gray", "indianred"] + blues
handles = [ plt.matplotlib.patches.Patch(label=l, facecolor=c,
        edgecolor="black", linewidth=.5)
    for l, c in zip(legend_labels, legend_colors) ]
legend = ax1.legend(handles=handles,
    loc="upper left", bbox_to_anchor=(1, 1),
    # handlelength=1, handleheight=.3,
    # handletextpad=,
    borderaxespad=0,
    labelspacing=.01,
    # columnspacing=,
    ncol=1, fontsize=6)

fig.align_ylabels()


export_pattern = "derivatives/sub-{subject}/sub-{subject}_task-{task}_acq-{acquisition}_hypno.png"
export_path = layout.build_path(bf.entities, export_pattern, validate=False)
utils.export_mpl(export_path)

