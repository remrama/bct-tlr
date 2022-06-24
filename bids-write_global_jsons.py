"""Generate a few global BIDS files specific to this study.
    root/dataset_description.json
    root/task-nap.json
"""
import os

import utils


bids_root = config.bids_root

dataset_description = {
    "Name": "BCT-TMR",
    "BIDSVersion": "1.7.0",
    "DatasetType": "raw",
    "License": "CCBY",
    "Authors": [
        "Remington Mallett",
        "Ken A. Paller"
    ],
    "Acknowledgements": "The good lord.",
    "HowToAcknowledge": "Please cite this paper: [link]",
    "Funding": [
        "Source 1",
        "Source 2"
    ],
      "EthicsApprovals": [
        "Source 1"
      ],
    "ReferencesAndLinks": [
        "paper link1",
        "paper link2"
    ],
    "DatasetDOI": "doi:10.0.2.3/dfjj.10",
    "HEDVersion": "8.0.0",
    "GeneratedBy": [
        {
            "Name": "reproin",
            "Version": "0.6.0",
            "Container": {
                "Type": "docker",
                "Tag": "repronim/reproin:0.6.0"
            }
        }
    ],
    "SourceDatasets": [
        {
            "URL": "s3://dicoms/studies/correlates",
            "Version": "April 11 2011"
        }
    ]
}

export_filepath = os.path.join(bids_root, "dataset_description.json")
utils.write_pretty_json(export_filepath)
