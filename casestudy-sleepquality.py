"""Compare sleep quality in sub-004 from study date to longitudinal followups."""

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

import utils


utils.set_matplotlib_style()


import_path1 = utils.ROOT_DIR / "phenotype" / "initial_survey.tsv"
import_path2 = utils.ROOT_DIR / "phenotype" / "sub-004_followup.tsv"

df1 = pd.read_csv(import_path1, sep="\t").query("ParticipantNum == 4")
df2 = pd.read_csv(import_path2, sep="\t")
meta1 = utils.import_json(import_path1.with_suffix(".json"))
meta2 = utils.import_json(import_path2.with_suffix(".json"))

# For the trait stuff (ie, not dream-report), can concat and drop anything without answers at all 3 timepoints.
df = pd.concat([df1, df2]).dropna(axis=1)
df.index = pd.Index(["week0", "week2", "week4"], name="timepoint")

### Calculate aggregate survey scores
# def imputed_sum(row):
#     if row.isna().mean() > .5:
#         # Return nan if more than half of responses are missing.
#         return np.nan
#     else:
#         return row.fillna(row.mean()).sum()
# def imputed_mean(row):
#     return np.nan if row.isna().mean() > .5 else row.fillna(row.mean()).mean()

# ISI
isi_columns = [ c for c in df if c.startswith("ISI") ]
df["ISI"] = df[isi_columns].sub(1).sum(axis=1)
df = df.drop(columns=isi_columns)

# LUSK
lusk_columns = [ c for c in df if c.startswith("LUSK") ]
df["LUSK"] = df[lusk_columns].mean(axis=1)
df = df.drop(columns=lusk_columns)


# Should probably change during source2raw...
df = df.rename(columns={"PSQ_1": "PSQI_1"})


psqi_columns = [ c for c in df if c.startswith("PSQI") ]


# Component 1 - Subjective sleep quality (Question 9)
component1 = df["PSQI_7"].sub(1)

# Component 2 - Sleep latency
component2a = pd.cut(df["PSQI_2"], [0, 16, 31, 61, np.inf], labels=[0., 1., 2., 3.], right=False).astype(float)
component2b = df["PSQI_5_1"].sub(1)
component2ab = component2a.add(component2b)
component2 = pd.cut(component2ab, [0, 1, 3, 5, np.inf], labels=[0, 1, 2, 3], right=False).astype(float)

# Component 3 - Sleep duration
# 35 and (maybe 1) are presumably typos
component3 = pd.cut(df["PSQI_4"], [0, 5, 6, 7, np.inf], labels=[3, 2, 1, 0], right=False).astype(float)

# Component 4 - Habitual sleep efficiency
sleep_duration_hours = df["PSQI_4"]
bedtime = pd.to_datetime(df["PSQI_1"], format="%H:%M")#, errors="coerce")  # errors for NAs
risetime = pd.to_datetime(df["PSQI_3"], format="%H:%M")#, errors="coerce")  # errors for NAs
risetime.loc[risetime.le(bedtime)] = risetime.add(pd.Timedelta("1day"))
bed_duration_hours = risetime.sub(bedtime).dt.seconds.div(60).div(60)
# assert sleep_duration_hours.le(bed_duration_hours).all()
efficiency = sleep_duration_hours.div(bed_duration_hours).mul(100)
component4 = pd.cut(efficiency, [0, 65, 75, 85, np.inf], labels=[0, 1, 2, 3], right=False).astype(float)

# Component 5 - Sleep disturbances
component5_columns = [ f"PSQI_5_{c}" for c in range(2, 11) ]
component5_sum = df[component5_columns].sub(1).sum(axis=1)
component5 = pd.cut(component5_sum, [0, 1, 10, 19, np.inf], labels=[0, 1, 2, 3], right=False).astype(float)

# Component 6 - Use of sleeping medication
component6 = df["PSQI_6_1"].sub(1)

# Component 7 - Daytime dysfunction
component7_sum = df["PSQI_6_2"].sub(1).add(df["PSQI_6_3"].sub(1))
component7 = pd.cut(component7_sum, [0, 1, 3, 5, np.inf], labels=[0, 1, 2, 3], right=False).astype(float)

# Global PSQI Score
df["PSQI_subjective"] = component1
df["PSQI_latency"] = component2
df["PSQI_duration"] = component3
df["PSQI_efficiency"] = component4
df["PSQI_disturbances"] = component5
df["PSQI_medication"] = component6
df["PSQI_dysfunction"] = component7

df["PSQI"] = component1.add(component2).add(component3).add(component4
    ).add(component5).add(component6).add(component7)

# PTSD Addendum
component8_columns = [ f"PSQI_8_{c}" for c in range(1, 8) ]
component8_sum = df[component8_columns].sub(1).sum(axis=1)
component8 = pd.cut(component8_sum, [0, 1, 10, 19, np.inf], labels=[0, 1, 2, 3], right=False).astype(float)
df["PSQI_ptsd"] = component8

### Week0 has NaNs so need to restuture to keep those if wanted.
# component9_columns = ["PSQI_9_1", "PSQI_9_2"]
# component9_sum = df[component9_columns].sub(1).sum(axis=1)
# component9 = pd.cut(component9_sum, [0, 1, 10, 19, np.inf], labels=[0, 1, 2, 3], right=False).astype(float)
# df["PSQI_ptsd2"] = component9

# df = df.drop(columns=psqi_columns)




# psqi_components = [ c for c in df if c.startswith("PSQI_") ]
# others = [ c for c in df if not c.startswith("PSQI_") ]
# df_long = df[others].melt(ignore_index=False).reset_index()
# g = sns.catplot(
#     data=df_long, x="timepoint", y="value", col="variable",
#     kind="bar",
#     height=2, aspect=0.7, col_wrap=4,
# )

# # g.set_axis_labels("", "Survival Rate")
# # g.set_xticklabels(["Men", "Women", "Children"])
# g.set_titles("{col_name}")


# DreamRecall, NightmareRecall, LucidRecall, LucidLastWeek

xvals = [0, 1, 2]
xticklabels = ["Lab\nVisit", "2-week\nFollowup", "4-week\nFollowup"]

df = df.reset_index()

# # Barplot showing baseline characteristics, all in one.
# bar_kwargs = dict(color="white", ec="black", lw=1)
# fig, ax = plt.subplots(figsize=(5, 3))
# ax.bar("variable", "value", data=df, **plot_kwargs)

plot_kwargs = {
    "color": "black",
    "markerfacecolor": "gainsboro",
    "markeredgecolor": "black",
    "linewidth": 1,
    "markeredgewidth": 1,
    "markersize": 10,
    "zorder": 10,
    "clip_on": False,
}


def plot(var, categorical=True):
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.plot("timepoint", var, "-o", data=df, **plot_kwargs)
    if var.endswith("Recall"):
        ylabel = var.split("Recall")[0] + " Recall"
    elif var.startswith("PSQI_"):
        probe = meta1[var]["Probe"]
        ylabel = probe.split(" - ")[1]
    elif var == "LucidLastWeek":
        ylabel = "# Lucid Dreams Last 2 Weeks"
    elif var == "LUSK":
        ylabel = "Lucid Dream Control (LUSK)"
    ax.set_xticks(xvals)
    ax.set_xticklabels(xticklabels)
    ax.set_ylabel(ylabel)
    ax.margins(x=0.2)
    if categorical:
        if var == "LUSK":
            var = "LUSK_1"  # All the same
        assert meta1[var]["Levels"] == meta2[var]["Levels"]
        yticks, yticklabels = zip(*meta1[var]["Levels"].items())
        yticks = [ int(y) for y in yticks ]
        yticklabels = [ y[::-1].replace(" ", "\n", 1)[::-1] for y in yticklabels ]
        # for i in range(len(yticklabels)):
        #     if i not in [0, len(yticklabels) - 1]:
        #         yticklabels[i] = ""
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels)
        ax.set_ylim(min(yticks) - 0.5, max(yticks) + 0.5)
    else:
        ax.set_ybound(lower=0)
        ax.yaxis.set_major_locator(plt.MultipleLocator(1))
    return fig, ax


for var in [
    "DreamRecall", "NightmareRecall", "LucidRecall", "LucidLastWeek",
    "PSQI_5_8", "PSQI_8_5", "LUSK",
    ]:
    categorical = var not in ["LucidLastWeek"]
    fig, ax = plot(var, categorical=categorical)
    export_path = utils.DERIVATIVES_DIR / "sub-004" / f"longitudinal_{var}.png"
    utils.export_mpl(export_path)
