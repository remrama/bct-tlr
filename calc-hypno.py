"""Export hypnogram tsv events files for a single subject. Some have 2 some have 1."""

import argparse

from bids import BIDSLayout
import mne
import pandas as pd
import tqdm
import yasa

import utils

mne.set_log_level(verbose=utils.MNE_VERBOSITY)

parser = argparse.ArgumentParser()
parser.add_argument("--participant", type=int, required=True)
parser.add_argument("--overwrite", action="store_true")
args = parser.parse_args()


participant = args.participant


import_path = utils.ROOT_DIR / "phenotype" / "initial_survey.tsv"
demogr = pd.read_csv(import_path, sep="\t")

if participant in demogr.index:
    age = demogr.loc[participant, "Age"]
    if age == 1:
        metadata = {"age": 20}
    elif age == 2:
        metadata = {"age": 30}
    elif age == 3:
        metadata = {"age": 40}
    elif age == 4:
        metadata = {"age": 50}
    elif age == 5:
        metadata = {"age": 60}
    elif age == 6:
        metadata = {"age": 70}

    gender = demogr.loc[participant, "Sex"]
    if gender in [1, 2]:
        metadata["male"] = True if gender == 1 else False
else:
    metadata = None

eeg_channel = "Fz"
eog_channel = "R-HEOG"
emg_channel = "EMG"
epoch_length = 30

layout = BIDSLayout(utils.ROOT_DIR, validate=False)
# stimuli_dir = bids_root / "stimuli"
bids_files = layout.get(
    subject=f"{participant:03d}",
    task="sleep",
    suffix="eeg",
    # extension=utils.EEG_RAW_EXTENSION,
    extension=".edf",
)

# Loop over each file and export a hypnogram events file.
for bf in tqdm.tqdm(bids_files, desc="Sleep Staging"):

    # Load raw data.
    # raw = mne.io.read_raw_fif(bf.path)
    raw = mne.io.read_raw_edf(bf.path)

    # Drop to the only channels needed for staging.
    raw.pick([eeg_channel, eog_channel, emg_channel])

    #### YASA ARTIFACT DETECTION

    # Load data.
    raw.load_data()

    # Perform YASA's automatic sleep staging.
    sls = yasa.SleepStaging(raw,
        eeg_name=eeg_channel,
        eog_name=eog_channel,
        emg_name=emg_channel,
        metadata=metadata,
    )

    hypno_str = sls.predict()
    hypno_proba = sls.predict_proba()
    hypno_proba = hypno_proba.add_prefix("proba_")
    # hypno_proba.columns = hypno_proba.columns.map("proba_{}".format)

    # Generate events dataframe for hypnogram.
    n_epochs = len(hypno_str)
    hypno_int = yasa.hypno_str_to_int(hypno_str)
    hypno_events = {
        "onset": [epoch_length*i for i in range(n_epochs)],
        "duration": [epoch_length for i in range(n_epochs)],
        "value" : hypno_int,
        "description" : hypno_str,
        "scorer": f"YASA-v{yasa.__version__}",
        "eeg_channel": eeg_channel,
        "eog_channel": eog_channel,
        "emg_channel": emg_channel,
    }
    hypno = pd.DataFrame.from_dict(hypno_events).join(hypno_proba.reset_index())

    hypno_sidecar = {
        "onset": {
            "LongName": "Onset (in seconds) of the event",
            "Description": "Onset (in seconds) of the event"
        },
        "duration": {
            "LongName": "Duration of the event (measured from onset) in seconds",
            "Description": "Duration of the event (measured from onset) in seconds"
        },
        "value": {
            "LongName": "Marker/trigger value associated with the event",
            "Description": "Marker/trigger value associated with the event"
        },
        "description": {
            "LongName": "Value description",
            "Description": "Readable explanation of value markers column"
        },
        "scorer": {},
        "eeg_channel": {},
        "eog_channel": {},
        "emg_channel": {}
    }
    for x in ["N1", "N2", "N3", "R", "W"]:
        hypno_sidecar[f"proba_{x}"] = {
            "LongName": f"Probability of {x}",
            "Description": f"YASA's estimation of {x} likelihood"
        }

    # Export.
    export_pattern = "derivatives/sub-{subject}/sub-{subject}_task-{task}_acq-{acquisition}_hypno.tsv"
    export_path = layout.build_path(bf.entities, export_pattern, validate=False)
    utils.export_tsv(hypno, export_path, index=False)
    utils.export_json(hypno_sidecar, export_path.replace(".tsv", ".json"))
