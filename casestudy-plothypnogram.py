"""Plot hypnogram(s) for a single subject. Might be two hypnos in one."""

from bids import BIDSLayout
import colorcet as cc
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yasa
import colorcet as cc
import matplotlib.colors as mcolors

import utils

utils.set_matplotlib_style()

participant_id = "sub-004"


import_path_nap_hypno = utils.ROOT_DIR / "derivatives" / participant_id / f"{participant_id}_task-sleep_acq-nap_hypno.tsv"
import_path_nap_events = utils.ROOT_DIR / participant_id / f"{participant_id}_task-sleep_acq-nap_events.tsv"
nap_hypno = pd.read_csv(import_path_nap_hypno, sep="\t")
nap_events = pd.read_csv(import_path_nap_events, sep="\t")
# overnight_hypno = pd.read_csv(import_path_nap_hypno.as_posix().replace("nap", "overnight"), sep="\t")
# overnight_events = pd.read_csv(import_path_nap_events.as_posix().replace("nap", "overnight"), sep="\t")

# Convert hypnogram stages to ints to ensure proper order.
stage_order = ["N3", "N2", "N1", "R", "W"]
stage_labels = ["SWS", "N2", "N1", "REM", "Wake"]
n_stages = len(stage_order)

hypno_int = nap_hypno["description"].map(stage_order.index).to_numpy()
hypno_secs = nap_hypno["duration"].mul(nap_hypno["epoch"]).to_numpy()
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

ev = nap_events.query("description.isin(['DreamReport', 'Cue'])")
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

ax0.broken_barh(xranges, yrange, facecolors=colors)
# ax0.eventplot(positions=cue_hrs, orienteation="horizontal",
#     lineoffsets=n_stages-.5, linelengths=1, linewidths=.1,
#     colors="mediumpurple", linestyles="solid")

# ax0.text(0, 1, "Deep breathing cues", color="mediumpurple",
#     ha="left", va="bottom", transform=ax0.transAxes)


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
probas = nap_hypno[["proba_N1", "proba_N2", "proba_N3", "proba_R", "proba_W"]].T.to_numpy()
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

ax1.set_ylabel("Sleep Stage\nConfidence")
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


# export_pattern = "derivatives/sub-{subject}/sub-{subject}_task-{task}_hypno.png"
# export_path = layout.build_path(bf.entities, export_pattern, validate=False)
ax1.set_xbound(upper=2.18)
export_path = utils.DERIVATIVES_DIR / "sub-004" / "hypnogram.png"
utils.export_mpl(export_path, close=False)
ax1.set_xlim(2.1, 2.18)
ax1.xaxis.set_major_locator(plt.MultipleLocator(30/60/60))
export_path = utils.DERIVATIVES_DIR / "sub-004" / "hypnogram_zoom.png"
utils.export_mpl(export_path)


###################### inception plot

# fig, ax = 
# bids_files = layout.get(
#     subject=f"{participant:03d}",
#     task="sleep",
#     suffix="eeg",
#     # extension=utils.EEG_RAW_EXTENSION,
#     extension=".edf",
# )
# bf = bids_files[0]
import mne
eeg_path = utils.ROOT_DIR / participant_id / f"{participant_id}_task-sleep_acq-nap_eeg.edf"

# # Testing
# raw = mne.io.read_raw_edf(eeg_path)
# # raw.crop(7766 - 134, 7766 + 134)
# raw.crop(7766 - 180, 7766 + 90)
# raw.pick(["Fz", "EMG", "L-VEOG", "R-HEOG", "Airflow", "RESP"])
# raw.load_data()
# channels = ["L-VEOG", "R-HEOG", "Fz", "EMG", "Airflow"]
# data = raw.get_data(picks=channels, return_times=False, units="uV")
# # plt.plot(data.T, label=channels)
# # plt.legend()
# fig, axes = plt.subplots(nrows=len(channels), sharex=True, sharey=False)
# for l, d, ax in zip(channels, data, axes.flat):
#     ax.plot(d, label=l)
#     ax.legend()
#     # ax.axvline(len(d)/2)
# plt.close()


# Real
raw = mne.io.read_raw_edf(eeg_path)
tlrlr = 7766
tmin = tlrlr - 180
tmax = tlrlr + 90
raw.crop(tmin, tmax)
channels = ["R-HEOG", "L-VEOG", "EMG", "Fz"]
raw.pick(channels)
times = raw.times
# data, times = raw.get_data(picks=channels, return_times=True, units="uV")

yticklabels = ["EOG", "EMG", "EEG"]

from matplotlib.collections import LineCollection
fig, axes = plt.subplots(nrows=2, figsize=(6, 3))
data, times = raw.get_data(picks=channels, return_times=True, units="uV")
segments = [ np.column_stack([times, x]) for x in data ]

colors = cc.glasbey_dark[:len(channels)]
colors = [ "black", "black", "black", "black" ]
colors = [ mcolors.to_rgba(c) for c in colors ]
linewidths = 0.3

n_rows = 3  # 2 EOG channels on one row
dmin = data.min()
dmax = data.max()
drange = dmax - dmin
ytickspacing = 0.6 * drange  # Crowd them a bit.
ymax = (n_rows - 1) * ytickspacing + dmax
# ax.set_ylim(dmin, ymax)
yticks = [ i * ytickspacing for i in range(n_rows) ]
offsets = [ (0, y) for y in yticks ]
offsets.insert(0, offsets[0])
for s, o in zip(segments, offsets):
    s[:, 1] += o[1]

ax, ax1 = axes
# ax.set_xlim(times.min(), times.max())
lines = LineCollection(segments,
    linewidths=linewidths, colors=colors,
    label=channels,
    # capstyle="butt", offsets=offsets, offset_transform=None,
)

ax.add_collection(lines)


# ax.set_ylabel(r"Voltage [$\mu$V]")
ax.set_yticks(yticks)
ax.set_yticklabels(yticklabels)
ax.spines[["left", "top", "right", "bottom"]].set_visible(False)
# ax.spines["left"].set_position(("outward", 5))
ax.tick_params(left=False, top=False, right=False, bottom=False)
ax.tick_params(labeltop=False, labelright=False, labelbottom=False)
ax.tick_params(direction="out")
ax.grid(False)
ax.margins(x=0, y=0)
# ax.set_ylim(-ylim, ylim)
# ax.patch.set_alpha(0)

errorbar_kwargs = dict(
    color="black", elinewidth=0.5, capthick=0.5, capsize=2, clip_on=False
)

# X-axis legend
ymin, ymax = ax.get_ylim()
ypad = 200
xsize = 30
xerr = xsize/2
xx = xsize/2
xy = ymax + ypad
xstring = f"{xsize:d} sec"
ysize = 300
yerr = ysize/2
yx = xx + xsize
yy = ymax + ypad + yerr
ystring = f" {ysize:d} " + r"$\mu$V"
ax.errorbar(xx, xy, xerr=xerr, **errorbar_kwargs)
ax.errorbar(yx, yy, yerr=yerr, **errorbar_kwargs)
ax.text(xx, xy, xstring, ha="center", va="bottom")
ax.text(yx, yy, ystring, ha="left", va="center")
ax.margins(x=0, y=0)


# ax.plot([30, 60], [10, 10], label="30s")
# ax.plot([90, 90], [10, 110], label="100uV")
# ax.legend()
# , 100, 90], [200, 300, 300])


# new colors to ensure other channels don't show up (if squished on first axis)
# colors = [ "none", colors[1], colors[2], "none"]
lines1 = LineCollection(segments, linewidths=linewidths, colors=colors, label=channels)
lines1 = LineCollection(
    segments[:2],
    linewidths=linewidths,
    colors=colors[:2],
    label=channels[:2],
)

ax1.add_collection(lines1)
zoom_xmin = tlrlr - tmin - 10  # some padding plus new tlrlr accounting for new zero
zoom_xmax = zoom_xmin + 40
zoom_ymin = max([segments[0][:, 1].min(), segments[1][:, 1].min()])
zoom_ymax = max([segments[0][:, 1].max(), segments[1][:, 1].max()])
ax1.set_xlim(zoom_xmin, zoom_xmax)
ax1.set_ylim(zoom_ymin, zoom_ymax)
# ax1.set_ylim(200, 900)

# ax.set_ylabel(r"Voltage [$\mu$V]")
# ax1.spines[["left", "top", "right", "bottom"]].set_visible(False)
ax1.tick_params(left=False, top=False, right=False, bottom=False)
ax1.tick_params(labelleft=False, labeltop=False, labelright=False, labelbottom=False)
ax1.grid(False)

_, conn_lines = ax.indicate_inset_zoom(ax1, edgecolor="black", alpha=1, linewidth=0.3)
for c in conn_lines:
    c.set_linewidth(0.3)

xpad = 1
ypad = 150
xsize = 5
xerr = xsize/2
xx = zoom_xmin + xpad + xsize/2
xy = zoom_ymax - ypad
xstring = f"{xsize:d} sec"
ysize = 150
yerr = ysize/2
yx = xx + xsize * 0.75
yy = zoom_ymax - ypad
ystring = f" {ysize:d} " + r"$\mu$V"
ax1.errorbar(xx, xy, xerr=xerr, **errorbar_kwargs)
ax1.errorbar(yx, yy, yerr=yerr, **errorbar_kwargs)
ax1.text(xx, xy, xstring, ha="center", va="bottom")
ax1.text(yx, yy, ystring, ha="left", va="center")
# ax1.margins(x=0, y=0)

export_path = utils.DERIVATIVES_DIR / "sub-004" / "hypnogram_zoom2.png"
utils.export_mpl(export_path)


ww
fig, axes = plt.subplots(
    nrows=3, figsize=(6, 4),
    sharex=True, sharey=False,
    gridspec_kw={"hspace": -0.7},
    constrained_layout=False,
)

plot_kwargs = dict(lw=0.5, clip_on=False)

eeg_data = raw.get_data(picks="Fz", units="uV")
eeg_lines = axes[1].plot(times, eeg_data.T, label="Fz", color="orchid", **plot_kwargs)

eog_data = raw.get_data(picks=["L-VEOG", "R-HEOG"], units="uV")
eog_lines = axes[2].plot(times, eog_data.T, label=["L-VEOG", "R-HEOG"], color="forestgreen", **plot_kwargs)
eog_lines[0].set_color("indianred")

emg_data = raw.get_data(picks="EMG", units="uV")
emg_lines = axes[0].plot(times, emg_data.T, label="EMG", color="royalblue", **plot_kwargs)

ylim = max([ max(map(abs, ax.get_ylim())) for ax in axes.flat ])

for ax, ch_type in zip(axes.flat, ["EEG", "EOG", "EMG"]):
    if ch_type == "EOG":
        ax.legend(loc="upper left")
    ax.set_ylabel(r"Voltage [$\mu$ V]")
    ax.set_yticks([0])
    ax.set_yticklabels([ch_type])
    ax.margins(x=0)
    ax.spines[["left", "top", "right", "bottom"]].set_visible(False)
    ax.spines["left"].set_position(("outward", 5))
    ax.tick_params(top=False, right=False, bottom=False, labeltop=False, labelright=False, labelbottom=False)
    ax.tick_params(direction="out")
    ax.set_ylim(-ylim, ylim)
    ax.patch.set_alpha(0)



# raw = mne.io.read_raw_edf(eeg_path)
# raw.crop(7766 - 180, 7766 + 90)
# raw.pick(["L-VEOG", "R-HEOG"])
# raw.load_data()
# channels = ["L-VEOG", "R-HEOG"]
# data, times = raw.get_data(picks=channels, return_times=True, units="uV")
# fig, ax = plt.subplots(figsize=(6, 1))
# lines = ax.plot(times, data.T, label=channels, color="black", lw=0.5)
# # lines[0].set_color("gainsboro")
# ax.legend()
# ax.set_ylabel(r"$\mu$V")
# ax.margins(x=0)
# ax.spines[["top", "right", "bottom"]].set_visible(False)
# ax.spines["left"].set_position(("outward", 5))
# ax.tick_params(top=False, right=False, bottom=False, labeltop=False, labelright=False, labelbottom=False)
# ax.tick_params(direction="out")
# ylim = max(map(abs, ax.get_ylim()))
# ax.set_ylim(-ylim, ylim)



# fig, ax = plt.subplots(figsize=(6, 1))
# mat = probas.argmax(axis=0).reshape(1,-1)
# ax.imshow(mat, aspect="auto", interpolation="none")


# stages = probas.argmax(axis=0)
# alphas = probas.max(axis=0)

# pall = ["blue", "green", "orchid", "indianred", "gray"]
# colors = [ pall[i] for i in stages ]
# mat2d = mcolors.to_rgba_array(colors, alphas)
# mat3d = np.expand_dims(mat2d, axis=0)
# fig, ax = plt.subplots(figsize=(6, 1))
# ax.imshow(mat3d, aspect="auto", interpolation="none")



