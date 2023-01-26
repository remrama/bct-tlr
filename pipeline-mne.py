"""MNE Preprocessing BIDS pipeline.
"""

from pathlib import Path

from bids import BIDSLayout
import mne
import pandas as pd

import utils

import dmlab


bids_root = utils.config.get("Paths", "bids_root")
# derivatives_dir = utils.config.get("Paths", "derivatives")

layout = BIDSLayout(bids_root, validate=False)
## Set validate to False so it allows .fif files.
## See restricting line here: https://github.com/bids-standard/pybids/blob/de3052e81d2d6e191d587308bad49fdfeb9c2c30/bids/layout/config/bids.json#L129

# Get all the nap files.
nap_paths = layout.get(
    scope="raw",
    subject="907",
    suffix="eeg",
    task="nap",
    extension=".fif",
    return_type="filename",
)

for eeg_path in nap_paths:

    entities = layout.parse_file_entities(eeg_path)
    # ## Weird thing where if the extension came from non-validation
    # ## it isn't parsed properly.
    # entities["extension"] = entities["extension"].split("'")[0]

    entities["extension"] = ".tsv"
    entities["suffix"] = "_hypno"
    # ## Compose directory location, though it seems like pybids
    # ## should do this automatically in build_path. That's the point, no?
    # ## Like isn't this just the same as making my own fstring?
    # path_template = Path(derivatives_dir) / "yasa" / "sub-{subject}" / "sub-{subject}_task-{task}{suffix}{extension}"
    # path_template = path_template.as_posix()
    # hypnogram_path = layout.build_path(entities, path_template, validate=False)
    # Path(hypnogram_path).parent.mkdir(parents=True, exist_ok=True)


    ############################################################
    # Re-referencing
    ############################################################

    # I think MNE loads with an average reference by default.
    mne.add_reference_channels(raw, "R-MSTD", copy=False)
    raw.set_eeg_reference(["L-MSTD", "R-MSTD"])
    # raw.drop_channels("L-MSTD")


    ############################################################
    # Marking bad channels
    ############################################################
    # https://mne.tools/stable/auto_tutorials/preprocessing/10_preprocessing_overview.html#sphx-glr-auto-tutorials-preprocessing-10-preprocessing-overview-py
    # https://mne.tools/stable/overview/cookbook.html#marking-bad-channels
    # https://mne.tools/stable/auto_tutorials/preprocessing/15_handling_bad_channels.html
    # *probably do manual inspection, or in real-time during data collection
    # autoreject (for epochs)

    ############################################################
    # Filtering
    ############################################################
    # Apply a bandpass filter to each channel.

    filter_params = dict(filter_length="auto", method="fir")
    filter_cutoffs = { # from AASM guidelines
        "eeg": (0.3, 35), # Hz; Low-cut, High-cut
        "eog": (0.3, 35),
        "emg": (10, 100),
        "ecg": (0.3, 70),
        "snoring": (10, 100),
        "respiration": (0.1, 15),
    }

    raw.filter(*filter_cutoffs["eeg"], picks="eeg", **filter_params)
    raw.filter(*filter_cutoffs["eog"], picks="eog", **filter_params)
    raw.filter(*filter_cutoffs["emg"], picks="emg", **filter_params)
    # raw.filter(*filter_cutoffs["ecg"], picks="ecg", **filter_params)
    raw.filter(*filter_cutoffs["snoring"], picks="Snoring", **filter_params)
    raw.filter(*filter_cutoffs["respiration"], picks=["RESP", "Airflow"], **filter_params)


    ############################################################
    # Artifact Suppression
    ############################################################
    # ICA


    ############################################################
    # Downsampling
    ############################################################
    # ICA


    ############################################################
    # Export
    ############################################################

    # Preprocessed raw file

    # MNE html report
    report = mne.Report(title='Raw example')
    # This method also accepts a path, e.g., raw=raw_path
    report.add_raw(raw=raw, title='Raw', psd=False)  # omit PSD plot
    report.save('report_raw.html', overwrite=True)
    report.add_events(events=events_path, title='Events from Path', sfreq=sfreq)
    ## Can add epochs
    ## Can add evokeds
    ## Can add covarience
    ## Can add ICA
    ## Can add code
    ## Can add custom figures
    ## CAN ADD A WHOLE FOLDER OF FILES so just do in separate script
    report.save('report_epochs.html', overwrite=True)
