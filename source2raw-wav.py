"""Copy raw wav file and convert speech-to-text (tsv) using Google Cloud Speech-to-text API."""

import argparse
import json
import os
from shutil import copyfile

import pandas as pd
from tqdm import tqdm
from google.cloud import storage
# from google.cloud import speech
from google.cloud import speech_v1p1beta1 as speech
from google.protobuf.json_format import MessageToDict

import utils


parser = argparse.ArgumentParser()
parser.add_argument("--delete", action="store_true", help="delete files in bucket after use")
parser.add_argument("--overwrite", action="store_true", help="overwrite local transcription")
args = parser.parse_args()


DELETE_BLOB_AFTER_CONVERSION = args.delete
OVERWRITE_LOCAL_TRANSCRIPTION = args.overwrite


#######################
# Validate credentials.
#######################

# Create Project
#   Create Bucket
#   Enable Speech2text API
#   Create Credentials / Add service account / export JSON
bucket_name = "bucket-of-dreams"
credentials_file = "./gcredentials.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file

###################################
# Initialize storage/bucket client.
###################################
storage_client = storage.Client()
bucket = storage_client.get_bucket(bucket_name)

###################################
# Initialize speech-to-text client.
###################################
config_kwargs = dict(
    # encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    # sample_rate_hertz=44100,
    language_code="en-US",
    max_alternatives=1,
    enable_automatic_punctuation=False,
    enable_word_confidence=True,
    enable_word_time_offsets=True,
    model="default", # phone_call, video
    use_enhanced=False,
    # diarization_config = speech.SpeakerDiarizationConfig(enable_speaker_diarization=True, min_speaker_count=2, max_speaker_count=2),
    diarization_config={
        "enable_speaker_diarization": True,
        "min_speaker_count": 2,
        "max_speaker_count": 2,
    },
)
speech_client = speech.SpeechClient()
config = speech.RecognitionConfig(**config_kwargs)

report_sidecar = {
    "speakerTag": {
        "LongName": "Unique speaker identifier",
        "Description": "",
    },
    "word": {
        "LongName": "Transcribed word",
        "Description": "",
    },
    "confidence": {
        "LongName": "Model confidence of transcribed word",
        "Description": "",
    },
    "startTime": {
        "LongName": "Start time in seconds in the wav file of this word",
        "Description": "",
    },
    "endTime": {
        "LongName": "End time in seconds in the wav file of this word",
        "Description": "",
    },
    "RecordingDevice": {
        "DeviceName": "",
        "SampleRate": "",
    },
    "TranscriptionModel": {
        "ModelName": "Google Cloud Speech-to-Text v1p1beta1",
        "ModelConfiguration": config_kwargs
    }
}


filepaths = list(utils.SOURCE_DIR.glob("*/*.wav"))[:1]

for path in (pbar := tqdm(filepaths)):

    # Parse path name and create export paths for new wav location and text conversion.
    participant_id = path.stem.split("_")[0]
    awakening_num = path.stem.split("-")[-1]
    export_name = f"{participant_id}_task-sleep_acq-nap_awk-{awakening_num:s}_report.wav"
    # export_name = path.name.replace("ses-001", "task-sleep_acq-nap").replace("report", "awk").replace(".", "_report.")
    export_path_wav = utils.ROOT_DIR / participant_id / export_name
    export_path_tsv = export_path_wav.with_suffix(".tsv")
    export_path_wav.parent.mkdir(parents=True, exist_ok=True)

    # Identify blob name/location in the bucket.
    blob = bucket.blob(path.name)

    ######################################
    # Copy source file into raw directory.
    ######################################
    pbar.set_description(f"Copying {path.name}")
    copyfile(path, export_path_wav)

    ##############################
    # Upload audio file to bucket.
    ##############################
    if not blob.exists():
        pbar.set_description(f"Uploading {path.name}")
        blob.upload_from_filename(path)

    #########################
    # Convert speech to text.
    #########################
    if not export_path_tsv.exists() or OVERWRITE_LOCAL_TRANSCRIPTION:
        pbar.set_description(f"Transcribing {path.name}")
        audio = speech.RecognitionAudio(uri=f"gs://{bucket_name}/{blob.name}")
        operation = speech_client.long_running_recognize(config=config, audio=audio)
        response = operation.result()
        # words = response.results[-1].alternatives[0].words
        words = MessageToDict(response.results[-1])["alternatives"][0]["words"]
        # words = MessageToDict(response._pb)["results"][-1]["alternatives"][0]["words"]
        # words = json.loads(type(response).to_json(response))["results"][-1]["alternatives"][0]["words"]
        df = pd.DataFrame(words)
        df["startTime"] = df["startTime"].str.rstrip("s").astype(float)
        df["endTime"] = df["endTime"].str.rstrip("s").astype(float)
        df = df[["speakerTag", "word", "confidence", "startTime", "endTime"]]
        utils.export_tsv(df, export_path_tsv, index=False)
        utils.export_json(report_sidecar, export_path_tsv.with_suffix(".json"))

    ##########################
    # Delete file from bucket.
    ##########################
    if DELETE_BLOB_AFTER_CONVERSION:
        pbar.set_description(f"Deleting {blob.name}")
        blob.delete()
