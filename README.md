# BCT TMR

## Display code

See `display` subdirectory and README.

## Analysis

Convert all data to BIDS format.

```shell
# Convert each Qualtrics survey file to a tsv in phenotype/
python source2raw-qualtrics.py --survey Initial+Survey      #> phenotype/initial_survey.tsv
python source2raw-qualtrics.py --survey Debriefing+Survey   #> phenotype/debriefing_survey.tsv
python source2raw-qualtrics.py --survey Dream+Report        #> phenotype/dream_report.tsv

# Convert participant behavior json/log files to tsv
python source2raw-bct.py            
#=> <sub>/beh/<sub>_task-bct_acq-pre_beh.tsv / .json
#=> <sub>/beh/<sub>_task-bct_acq-post_beh.tsv / .json

# Dream report Qualtrics file is used for events file or a separate awakenings file.

# Convert each participant's EEG file to multiple task files.
python source2raw-survey.py
#=> <sub>/<sub>_scans.tsv / json
#=> <sub>/eeg/<sub>_task-sleep_<run>_eeg.fif / .json
#=> <sub>/eeg/<sub>_task-sleep_<run>_events.tsv / .json
#=> <sub>/eeg/<sub>_task-sleep_<run>_channels.tsv / .json
#=> <sub>/eeg/<sub>_task-bct_acq-pre_eeg.fif [events, channels]
#=> <sub>/eeg/<sub>_task-bct_acq-post_eeg.fif [events, channels]
#=> <sub>/eeg/<sub>_task-att_acq-pre_eeg.fif [events, channels]
#=> <sub>/eeg/<sub>_task-att_acq-post_eeg.fif [events, channels]
#=> <sub>/eeg/<sub>_task-mw_acq-pre_eeg.fif [events, channels]
#=> <sub>/eeg/<sub>_task-mw_acq-post_eeg.fif [events, channels]
```
