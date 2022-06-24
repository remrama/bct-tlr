"""Helper functions"""

import configparser
import json
import os
import sys

# Load configuration file so it's accessible from utils
config = configparser.ConfigParser(converters={"list": json.loads})
config.read("./config.ini")

# Add development dir while working on dmlab.
sys.path.append("C:/Users/malle/packages/dmlab")

def _check_bids_root_exists():
    # make sure BIDS root directory exists
    bids_root = config.get("Paths", "bids_root")

def make_pathdir_if_not_exists(filepath):
    directory = os.path.dirname(filepath)
    os.makedirs(directory, exist_ok=True)

def write_pretty_json(obj, filepath):
    with open(filepath, "w", encoding="utf-8") as fp:
        json.dump(obj, fp, indent=4, sort_keys=False, ensure_ascii=True)