"""Compare the 3 dream reports, baseline and 2 followups."""

import textwrap

from bids import BIDSLayout
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt; plt.ion()
import seaborn as sns

import utils


utils.set_matplotlib_style()

import_path1 = utils.ROOT_DIR / "phenotype" / "dream_report.tsv"
import_path2 = utils.ROOT_DIR / "phenotype" / "debriefing_survey.tsv"
import_path3 = utils.ROOT_DIR / "phenotype" / "sub-004_followup.tsv"

df1 = pd.read_csv(import_path1, sep="\t").query("ParticipantNum == 4")
df2 = pd.read_csv(import_path2, sep="\t").query("ParticipantNum == 4")
df3 = pd.read_csv(import_path3, sep="\t")
meta1 = utils.import_json(import_path1.with_suffix(".json"))
meta2 = utils.import_json(import_path2.with_suffix(".json"))
meta3 = utils.import_json(import_path3.with_suffix(".json"))


# For the trait stuff (ie, not dream-report), can concat and drop anything without answers at all 3 timepoints.
# df = pd.concat([df1, df2]).dropna(axis=1)
# df.index = pd.Index(["week0", "week2", "week4"], name="timepoint")
df1 = df1[["Report", "Recall", "Lucidity", "LRLR", "Control", "Valence"]]
df2 = df2[["DreamReport", "DreamArousal_1", "DreamPleasure_1"]]
lusk_columns = [ c for c in df3 if c.startswith("LUSK_") ]
df3["LUSK"] = df3[lusk_columns].mean(axis=1)
df3 = df3.drop(columns=lusk_columns)
df3 = df3[
    [
        "Report", "Nightmare",
        "Reflection", "Lucidity", "Control", "LUSK",
        "ValencePrelucid", "ValenceLucid", "Valence",
        "LucidHelpHarm", "VisitImpact", "Extra",
    ]
]
df3.index = pd.Index(["week2", "week4"], name="timepoint")



################################################################################
# Valence X Lucidity PLOT
################################################################################

yser = df3.loc["week2", ["ValencePrelucid", "ValenceLucid"]]
xvals = [0, 1]
xticklabels = ["Before\nLucidity", "During\nLucidity"]
yvals = yser.to_numpy()
cvals = ["white", "white"]
bar_kwargs = dict(lw=1, ec="black")

assert meta3["ValencePrelucid"]["Levels"] == meta3["ValenceLucid"]["Levels"]
yticks, yticklabels = zip(*meta3["ValenceLucid"]["Levels"].items())
yticks = [ int(y) for y in yticks ]
yticklabels = [ y.replace(" ", "\n") for y in reversed(yticklabels) ]
yticklabels[1] = ""
yticklabels[2] = "Neutral"
yticklabels[3] = ""
ylabel = "Valence"

xlabel = "While dreaming\n" + r"$\rightarrow$"

yticks = [ y - 1 for y in yticks ]
yvals = [ 5 - y for y in yvals ]

fig, ax = plt.subplots(figsize=(3, 3))
ax.bar(xvals, yvals, color=cvals, **bar_kwargs)
ax.set_ylabel(ylabel)
ax.set_yticks(yticks)
ax.set_xticks(xvals)
ax.set_xticklabels(xticklabels)
ax.set_yticklabels(yticklabels)
ax.set_xlim(-1, 2)
# ax.set_ylim(yticks[0], yticks[-1])
ax.set_xlabel(xlabel)
ax.set_ybound(upper=4.3)

export_path = utils.DERIVATIVES_DIR / "sub-004" / "longitudinal_ValenceLucidity.png"
utils.export_mpl(export_path)


################################################################################
# LAB DREAM CHARACTERISTICS
################################################################################

xwrapper = textwrap.TextWrapper(width=9, break_long_words=False, max_lines=3, placeholder=" [...]")
ywrapper = textwrap.TextWrapper(width=20, break_long_words=False, max_lines=4, placeholder=" [...]")

ser1 = df1.squeeze()
yorder = ["Recall", "Lucidity", "LRLR", "Control", "Valence"]
ser1 = ser1.loc[yorder]

# fig, ax = plt.subplots(figsize=(5, 1))


def plot_likert(vars_list, ax):
    if not isinstance(vars_list, list):
        vars_list = [vars_list]
    yticks = []
    yticklabels = []
    for i, var in enumerate(vars_list):
        probe, levels = meta1[var].values()
        xticks, xticklabels = zip(*levels.items())
        xticks = [ int(x) for x in xticks ]
        xticklabels = [ xwrapper.fill(x) for x in xticklabels ]
        ylabel = ywrapper.fill(probe)
        yticks.append(i)
        yticklabels.append(ylabel)
        scatter_kwargs = {
            "s": 200,
            "marker": "o",
            "edgecolors": "black",
        }
        # linewidths = np.full_like(xticks, 1)
        response = ser1.at[var]
        linewidths = [ 2 if x == response else 1 for x in xticks ]
        colors = [ "black" if x == response else "white" for x in xticks ]
        ax.scatter(xticks, np.full_like(xticks, i), c=colors, linewidths=linewidths, **scatter_kwargs)
    ax.set_xlim(min(xticks) - 0.5, max(xticks) + 0.5)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)
    ax.set_ylim(min(yticks) - 0.5, max(yticks) + 0.5)
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)
    # ax.set_ylabel(ylabel, rotation=0, ha="right", va="center")
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    # ax.spines["left"].set_position(("outward", 5))
    ax.tick_params(left=True, top=False, right=False, bottom=False)
    ax.tick_params(labelleft=True, labeltop=True, labelright=False, labelbottom=False)
    ax.tick_params(direction="out")


fig, axes = plt.subplots(nrows=3, figsize=(5, 4), sharex=False, sharey=False,
    gridspec_kw={"height_ratios": [1, 3, 1]})

plot_likert("Recall", axes[0])
plot_likert(["LRLR", "Control", "Lucidity"], axes[1])
plot_likert("Valence", axes[2])

# xmax = max([ max(map(abs, ax.get_xlim())) for ax in axes ])
xmax = max([ ax.get_xlim()[1] for ax in axes ])
for ax in axes:
    ax.set_xbound(upper=xmax)

export_path = utils.DERIVATIVES_DIR / "sub-004" / "longitudinal_LabReportLikerts.png"
utils.export_mpl(export_path)
