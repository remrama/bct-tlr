"""
Run all YASA analyses.
Export to a new derivatives/yasa directory
and follow BIDS-formatting, including dataset_description.
"""

from pathlib import Path

from bids import BIDSLayout
import mne
import pandas as pd
import yasa

import utils

import dmlab


bids_root = utils.config.get("Paths", "bids_root")
derivatives_dir = utils.config.get("Paths", "derivatives")

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

    # Generate hypnogram filepath for exporting.
    entities = layout.parse_file_entities(eeg_path)
    # ## Weird thing where if the extension came from non-validation
    # ## it isn't parsed properly.
    # entities["extension"] = entities["extension"].split("'")[0]
    entities["extension"] = ".tsv"
    entities["suffix"] = "_hypno"
    ## Compose directory location, though it seems like pybids
    ## should do this automatically in build_path. That's the point, no?
    ## Like isn't this just the same as making my own fstring?
    path_template = Path(derivatives_dir) / "yasa" / "sub-{subject}" / "sub-{subject}_task-{task}{suffix}{extension}"
    path_template = path_template.as_posix()
    hypnogram_path = layout.build_path(entities, path_template, validate=False)
    Path(hypnogram_path).parent.mkdir(parents=True, exist_ok=True)

    # Load EEG data and extra info.
    raw = mne.io.read_raw(eeg_path)


    #####################################################
    # Preprocessing
    #####################################################
    
    # Pull YASA staging parameters from configuration file.
    eeg_channel = "Fz"
    eog_channel = "R-HEOG"
    emg_channel = "EMG"

    # Drop to the only channels needed for staging.
    raw.pick([eeg_channel, eog_channel, emg_channel])

    # Load data into memory.
    raw.load_data(verbose=None)

    # Downsample to 100 Hz.
    raw.resample(100)


    #####################################################
    # Sleep Staging
    #####################################################

    # Predict stages for each epoch.
    hypnogram_str = yasa.SleepStaging(raw,
        eeg_name=eeg_channel,
        eog_name=eog_channel,
        emg_name=emg_channel
    ).predict()

    # # Detect motion artifacts.
    # raw_eeg_only = raw.pick_types(eeg=True)
    # hypnogram_int = yasa.hypno_str_to_int(hypnogram_str)
    # hypnogram_int_upsampled = yasa.hypno_upsample_to_data(
    #     hypnogram_int,
    #     1/config.getint("DEFAULT", "epoch_length"),
    #     raw_eeg_only)
    # art_epochs, _ = yasa.art_detect(raw_eeg_only, hypno=hypnogram_int_upsampled)
    # print(art_epochs)
    # print(len(art_epochs), len(hypnogram_str))
    # hypnogram_str_w_art = [ -1 if artifact else hypnogram_str[i]
    #     for i, artifact in enumerate(art_epochs) ]
    # print(hypnogram_str_w_art)

    # Generate events dataframe for hypnogram.
    epoch_length = 30
    hypnogram_int = yasa.hypno_str_to_int(hypnogram_str)
    hypnogram_events = {
        "onset": [ epoch_length*i for i in range(len(hypnogram_str)) ],
        "duration": [ epoch_length for i in range(len(hypnogram_str)) ],
        "value" : hypnogram_int,
        "description" : hypnogram_str,
    }
    hypnogram_df = pd.DataFrame.from_dict(hypnogram_events)

    # Export.
    dmlab.io.export_dataframe(hypnogram_df, hypnogram_path)



    #####################################################
    # Detection Algorithms
    #####################################################

    # Spindles
    # Drop to the only channels needed for staging.
    raw.pick_types(eeg=True)
    sp = yasa.spindles_detect(raw)
    # ax = sp.plot_average(center='Peak', time_before=0.8, time_after=0.8, filt=(12, 16), ci=None)
    # df_sync = sp.get_sync_events(center='Peak', time_before=0.8, time_after=0.8)
    # coincidence = sp.get_coincidence_matrix()
    sp.summary().to_csv(export_path, sep="\t", index=False)
