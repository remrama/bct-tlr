"""How many cues were played and in what sleep stages?

Also get length and volume, later when SMACC info is merged again.
"""
import argparse

from bids import BIDSLayout
import numpy as np
import pandas as pd
import yasa

import utils


parser = argparse.ArgumentParser()
parser.add_argument("--participant", type=int, required=True)
args = parser.parse_args()

participant = args.participant


layout = BIDSLayout(utils.ROOT_DIR, derivatives=True, validate=False)
bids_files = layout.get(subject=f"{participant:03d}",
    task="sleep",
    acquisition="nap",
    # suffix="hypno",
    extension=".tsv",
    # return_type="filename",
)

for bf in bids_files:
    if bf.entities["suffix"] == "hypno":
        hypno = bf.get_df()
    elif bf.entities["suffix"] == "events" and bf.dirname.endswith("eeg"):  # temp bc old files outside eeg/
        events = bf.get_df()

events = events.query("description.eq('Cue')")

bins = [(x, x+y) for x, y in zip(hypno["onset"], hypno["duration"])]
duration = hypno["duration"].unique()[0]
bins = hypno["onset"].to_numpy()
bins = np.append(bins, bins[-1]+duration)
cue_onsets = events["onset"].to_numpy()

# Approach #1
labels = hypno.index.tolist()
cut = pd.cut(cue_onsets, bins=bins, labels=labels)
cued_epochs = cut.to_list()
hypno["cued"] = False
hypno.loc[cued_epochs, "cued"] = True
freqs = hypno.groupby("description")["cued"].sum().rename("frequency").rename_axis("stage")

# # Approach #2
# labels = hypno["description"].tolist()
# cut = pd.cut(cue_onsets, bins=bins, labels=labels, ordered=False)
# freqs = cut.value_counts()

export_pattern = "derivatives/sub-{subject}/sub-{subject}_task-{task}_acq-{acquisition}_cues.tsv"
export_path = layout.build_path(bf.entities, export_pattern, validate=False)
utils.export_tsv(freqs, export_path, index=True)
