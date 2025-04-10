import time
import numpy as np
import os 
import json
import requests


def connect_to_source():
    pass

def connect_to_destination():
    pass

def ingest_data_from_source(source, object, params, source_creds):
    return {}

def move_data_to_destination(data, params, dest, dest_creds):
    pass

def move_data():
    try:
        source = os.getenv('SOURCE') ## Set in Orchestra Pipeline Task
        obj = os.getenv('OBJECT') ## Set in Orchestra Pipeline Task
        params = os.getenv('PARAMS') ## Set in Orchestra Pipeline Task
        dest = os.getenv('DESTINATION') ## Set in Orchestra Pipeline Task

        source_creds = os.getenv('SOURCE_CREDS') ## Set in Orchestra Python Connection
        dest_creds = os.getenv('DEST_CREDS') ## Set in Orchestra Python Connection

        data = ingest_data_from_source(source, pbj, params, source_creds)
        move_data_to_destination(data, params, dest, dest_creds)
    except Exception as e:
        raise Exception("Pipeline did not complete due to: " + str(e))

def set_orchestra_output(output_name: str, output_value:str):
    """
    Use this function to set an output on the Task Run that can be used by downstream tasks
    """
    data = {
        "event_type": "SET_OUTPUT",
        "task_run_id": os.getenv('ORCHESTRA_TASK_RUN_ID'),  # Set Automatically
        "output_name": output_name,
        "output_value": output_value
    }

    url = "https://webhook.getorchestra.io"
    api_key = os.getenv('ORCHESTRA_API_KEY') ## Set in Orchestra Python Connection
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" 
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    # Print the response
    print(response.status_code)
    print(response.text)
    if response.status_code != 200:
        raise Exception("")


if __name__ == "__main__":
    print("Hello, World!")