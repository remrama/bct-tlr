"""Convert a single qualtrics survey to tsv and companion json."""

import argparse
from pathlib import Path

import numpy as np
import pyreadstat

import utils


parser = argparse.ArgumentParser()
parser.add_argument(
    "-s",
    "--survey",
    type=str,
    required=True,
    choices=["Initial+Survey", "Debriefing+Survey", "Dream+Report"],
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
}

# Identify location to import from and export to, and make sure export directory exists.
import_dir = utils.ROOT_DIR / "sourcedata"
export_dir = utils.ROOT_DIR / "phenotype"

# Find the relevant file with a glob-search and confirming filename to Qualtrics convention.
glob_name = f"*{survey_name}*.sav"
potential_import_paths = list(import_dir.glob(glob_name))
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
        column_info["Levels"] = meta.variable_value_labels[col]
    if column_info:
        sidecar[col] = column_info


################################################################################
# EXPORTING
################################################################################

# Replace empty strings with NaNs.
df = df.replace("", np.nan)

export_name = survey_name.lower().replace("+", "_") + ".tsv"
export_path_data = export_dir / export_name
export_path_sidecar = export_path_data.with_suffix(".json")

utils.export_tsv(df, export_path_data, index=False)
utils.export_json(sidecar, export_path_sidecar)
