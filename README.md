# BCT TMR

## Display code

See `display` subdirectory and README.

## Analysis

Convert all data to BIDS format.

```shell
# Convert each participant's EEG file to multiple edf files.
python source2raw-eeg.py

# Convert each Qualtrics survey file to tsv.
python source2raw-qualtrics.py --survey Initial+Survey      #> phenotype/initial_survey.tsv
python source2raw-qualtrics.py --survey Debriefing+Survey   #> phenotype/debriefing_survey.tsv
python source2raw-qualtrics.py --survey Dream+Report        #> separate subject files

# Move dream reports wav recordings to raw, and convert to text.
python source2raw-wav.py

# Convert participant behavior json/log files to tsv
python source2raw-bct.py


```
