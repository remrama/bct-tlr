# BCT TMR

## Display code

See `display` subdirectory and README.

## Analysis

See `runall.sh` for script order and details.

```shell
set -e

# For each participant...
for p in 907 908 909 1 2 3 4 5
do
    # ...convert EEG file to separate BIDS-formatted edf (and associated) files.
    python source2raw-eeg.py --participant $p
    # ...calculate their hypnogram(s).
    python calc-hypno.py --participant $p
    # ...plot their hypnogram(s).
    python plot-hypno.py --participant $p
    # ...calculate number of cues per sleep stage.
    python calc-cues.py --participants $p
    # ...calculate respiration rate variability features.
    python calc-rrv.py --participant $p
done

# Convert each Qualtrics survey file to tsv.
python source2raw-qualtrics.py --survey Initial+Survey      #> phenotype/initial_survey.tsv
python source2raw-qualtrics.py --survey Debriefing+Survey   #> phenotype/debriefing_survey.tsv
python source2raw-qualtrics.py --survey Dream+Report        #> separate subject files
python source2raw-qualtrics.py --survey sub-004+Followup
# Convert Breath-Counting Task behavior json/log files to tsv files.
python source2raw-bct.py
# Move dream reports wav recordings to raw, and convert to text.
python source2raw-wav.py

# Compare group pre-nap and post-nap BCT performance.
python plot-bct.py
```
