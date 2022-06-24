"""Plot all BCT presses of all participants.
"""

from pathlib import Path

from bids import BIDSLayout
import pandas as pd

import utils

import dmlab


bids_root = utils.config.get("Paths", "bids_root")
derivatives_dir = utils.config.get("Paths", "derivatives")

export_filepath = Path(derivatives_dir) / "derivatives" / "matplotlib" / "bct-presses.png"

layout = BIDSLayout(bids_root)

# Get all the BCT files.
bids_files = layout.get(
    suffix="beh",
    task="bct",
    extension=".tsv",
    acquisition=["pre", "post"],
    return_type="object",
)

# Stack all participants into one dataframe.
dataframes = []
for bf in bids_files:
    _df = bf.get_df()
    entities = bf.get_entities()
    _df.insert(0, "participant_id", "sub-"+entities["subject"])
    _df.insert(1, "acquisition_id", "acq-"+entities["acquisition"])
    dataframes.append(_df)

df = pd.concat(dataframes)

# Draw and save plot using DML package.
fig = dmlab.bct.plot_presses(df, export_filepath, participant="participant_id")
