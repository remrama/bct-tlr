"""Convert a single qualtrics survey to tsv and companion json."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

import utils


parser = argparse.ArgumentParser()
parser.add_argument(
    "--survey",
    type=str,
    required=True,
    choices=["Initial+Survey", "Debriefing+Survey", "Dream+Report", "sub-004+Followup"],
)
args = parser.parse_args()

survey_name = args.survey


################################################################################
# SETUP
################################################################################

survey_descriptions = {
    "Initial+Survey": "A survey of demographics and state measures, completed before tasks.",
    "Debriefing+Survey": "A survey of more demographics, state measures, and debriefing questions, completed after tasks",
    "Dream+Report": "A dream report, completed immediately after an experimental awakening.",
    "sub-004+Followup": "TODO",
}

# Identify location to import from and export to, and make sure export directory exists.
source_dir = utils.SOURCE_DIR
phenotype_dir = utils.ROOT_DIR / "phenotype"
raw_dir = utils.ROOT_DIR

# Find the relevant file with a glob-search and confirming filename to Qualtrics convention.
glob_name = f"*{survey_name}*.sav"
potential_import_paths = list(source_dir.glob(glob_name))
assert len(potential_import_paths) == 1, "Only the latest Qualtrics file should be present."
import_path = potential_import_paths[0]

# Load the Qualtrics survey data and metadata.
df, meta = pyreadstat.read_sav(import_path)


################################################################################
# PREPROCESSING
################################################################################


# Add timezone information to timestamps.
df["RecordedDate"] = df["RecordedDate"].dt.tz_localize("US/Mountain")
df["StartDate"] = df["StartDate"].dt.tz_localize("US/Mountain")
df["EndDate"] = df["EndDate"].dt.tz_localize("US/Mountain")

# Remove piloting/testing data and anyone who closed the survey out early.
df = (df
    .query("DistributionChannel == 'anonymous'")
    .query("Status == 0")
    .query("Finished == 1")
    .query("Progress == 100")
)

assert df["ResponseId"].is_unique, "Unexpectedly found non-unique Response IDs."
assert df["UserLanguage"].eq("EN").all(), "Unexpectedly found non-English responses."

# Remove default Qualtrics columns.
default_qualtrics_columns = [
    "StartDate",
    "EndDate",
    "RecordedDate",
    "Status",
    "DistributionChannel",
    "Progress",
    "Finished",
    "ResponseId",
    "UserLanguage",
    "Duration__in_seconds_",
]
df = df.drop(columns=default_qualtrics_columns)


# Validate Likert scales.
# Sometimes when the Qualtrics question is edited, the scale gets changed "unknowingly".
# Here, check to make sure everything starts at 1 and increases by 1.
for var in df:
    if var in meta.variable_value_labels:
        levels = meta.variable_value_labels[var]
        values = list(levels.keys())
        assert values[0] == 1, f"{var} doesn't start at 1, recode in Qualtrics."
        assert values == sorted(values), f"{var} isn't increasing, recode in Qualtrics."
        assert not np.any(np.diff(values) != 1), f"{var} isn't linear, recode in Qualtrics."


################################################################################
# GENERATING BIDS SIDECAR
################################################################################


# Generate BIDS sidecar with column metadata.
sidecar = {
    "MeasurementToolMetadata": {
        "Description": survey_descriptions[survey_name],
    }
}
for col in df:
    column_info = {}
    # Get probe string (if present).
    if col in meta.column_names_to_labels:
        column_info["Probe"] = meta.column_names_to_labels[col]
    # Get response option strings (if present).
    if col in meta.variable_value_labels:
        levels = meta.variable_value_labels[col]
        levels = { int(float(k)): v for k, v in levels.items() }
        column_info["Levels"] = levels
    if column_info:
        sidecar[col] = column_info


################################################################################
# EXPORTING
################################################################################

# Replace empty strings with NaNs.
df = df.replace("", np.nan)

df["ParticipantNum"] = df["ParticipantNum"].astype(int).map("sub-{:03d}".format)
df["SessionNum"] = df["SessionNum"].astype(int).map("ses-{:03d}".format)
df = df.rename(columns={"ParticipantNum": "participant_id", "SessionNum": "session_id"})

if survey_name == "Dream+Report":
    df = df.rename(columns={"AwakeningNum": "awakening_id"})
    df["awakening_id"] = df["awakening_id"].astype(int).map("awk-{:02d}".format)
    assert not df.duplicated(subset=["participant_id", "session_id", "awakening_id"]).any()
    for (subject, session), awakenings in df.groupby(["participant_id", "session_id"]):
        export_name = f"{subject}_task-sleep_acq-nap_rep.tsv"
        export_path = raw_dir / subject / "rep" / export_name
        awakenings = awakenings.drop(columns=["participant_id", "session_id"])

        # Get onset of each awakening wrt the EEG file.
        # Some subjects it doesn't match up? haven't looked much into it yet
        if subject not in ["sub-906", "sub-908"]:
            n_awakenings = len(awakenings)
            report_onsets = []
            for acq in ["overnight", "nap"]:
                import_path_events = raw_dir / subject / "eeg" / f"{subject}_task-sleep_acq-{acq}_events.tsv"
                if Path(import_path_events).exists():
                    events = pd.read_csv(import_path_events, sep="\t")
                    if "DreamReport" in events["description"].values:
                        onsets = events.loc[events["description"].eq("DreamReport"), "onset"].tolist()
                        report_onsets.extend(onsets)
            n_reports = len(report_onsets)
            assert n_awakenings == n_reports, (
                f"Number of awakenings {n_awakenings} should match the number of "
                f"Dream Reports {n_reports} in EEG events file."
            )
            awakenings.insert(1, "onset", report_onsets)

            sidecar["onset"] = utils.import_json(import_path_events.with_suffix(".json"))["onset"]

        utils.export_tsv(awakenings, export_path, index=False)
        utils.export_json(sidecar, export_path.with_suffix(".json"))
else:
    export_name = survey_name.lower().replace("+", "_") + ".tsv"
    export_path = phenotype_dir / export_name
    utils.export_tsv(df, export_path, index=False)
    utils.export_json(sidecar, export_path.with_suffix(".json"))
