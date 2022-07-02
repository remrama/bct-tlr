"""Convert a single qualtrics survey to tsv.
"""

from pathlib import Path

import utils

import dmlab

surveys = {
    "Initial Survey": "A welcome survey",
    # "Debriefing Survey": "A debriefing survey",
    "Dream Report": "A dream report",
}

raw_dir = utils.config.get("Paths", "raw")
phenotype_dir = Path(raw_dir) / "phenotype"
phenotype_dir.mkdir(parents=False, exist_ok=True)


source_dir = Path(utils.config.get("Paths", "source"))

for name, description in surveys.items():

    glob_name = "*" + name.replace(" ", "+") + "*.sav"
    potential_paths = source_dir.glob(glob_name)

    potential_paths = list(potential_paths)
    filepath = dmlab.qualtrics.latest_sourcepath(potential_paths)
    df, meta = dmlab.qualtrics.load_spss(filepath, cleanse=True)

    dmlab.qualtrics.validate_likert_scales(meta, df.columns)
    sidecar = dmlab.qualtrics.generate_bids_sidecar(df, meta, description)

    export_stem = name.lower().replace(" ", "_")
    data_filepath = phenotype_dir.joinpath(export_stem).with_suffix(".tsv")
    sidecar_filepath = data_filepath.with_suffix(".json")
    
    dmlab.io.export_dataframe(df, data_filepath)
    dmlab.io.export_json(sidecar, sidecar_filepath)