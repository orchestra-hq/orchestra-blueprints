from azure.storage.filedatalake import DataLakeServiceClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import requests
import os

def get_service_client_token_credential(account_name) -> DataLakeServiceClient:
    account_url = f"https://{account_name}.dfs.core.windows.net"
    token_credential = DefaultAzureCredential()

    service_client = DataLakeServiceClient(account_url, credential=token_credential)

    return service_client

def get_blob_service_client(blob_accnt_name):
    _blob_acct_url = f'https://{blob_accnt_name}.blob.core.windows.net'
    token_credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=_blob_acct_url, credential=token_credential)

def get_container_client(blob_client:BlobServiceClient, container:str):
    return blob_client.get_container_client(container)

from datetime import datetime, timedelta

def is_within_last_hour(dt, hours):
    """
    Check if the provided datetime object `dt` is within the last hour.

    Args:
    dt (datetime.datetime): The datetime object to check.

    Returns:
    bool: True if `dt` is within the last hour, False otherwise.
    """
    now = datetime.now(dt.tzinfo)  # Ensure timezone compatibility
    one_hour_ago = now - timedelta(hours=hours)
    return one_hour_ago <= dt <= now

def is_within_last_minutes(dt, minutes):
    """
    Check if the provided datetime object `dt` is within the last hour.

    Args:
    dt (datetime.datetime): The datetime object to check.

    Returns:
    bool: True if `dt` is within the last hour, False otherwise.
    """
    now = datetime.now(dt.tzinfo)  # Ensure timezone compatibility
    one_hour_ago = now - timedelta(minutes=minutes)
    return one_hour_ago <= dt <= now

def run_adls_sensor_python(blob_path:str, container_path:str, duration_hours:int, pipeline_id):
    account_name = f'https://{blob_path}.blob.core.windows.net/{container_path}'
    blob_client = get_blob_service_client(blob_path)
    container_client = get_container_client(blob_client, container_path)
    blobs = container_client.list_blobs()
    blobs_to_download =[i.get('name') for i in blobs if is_within_last_hour(i.get('creation_time'), duration_hours)]
    print(blobs_to_download)
    
    if len(blobs_to_download) > 0:
        orchestra_token = os.get_env('ORCHESTRA_TOKEN')
        url = f"https://app.getorchestra.io/engine/public/pipelines/{pipeline_id}/start"
        headers = {
        'Authorization': f'Bearer {orchestra_token}'
        }
        response = requests.request("POST", url, headers=headers)
    else:
        """Add Custom Alerting here"""
        raise Exception("No file Found")

def get_client(blob_path:str, container_path:str):
    blob_client = get_blob_service_client(blob_path)
    return get_container_client(blob_client, container_path)

def authenticate(blob_path:str, container_path:str):
    account_name = f'https://{blob_path}.blob.core.windows.net/{container_path}'
    container_client = get_client(blob_path, container_path)
    items = container_client.get_container_properties().items()
    for i in items:
        print(i)
    return

def start(blob_path:str, container_path:str, minutes: int):
    container_client = get_client(blob_path:str, container_path:str):
    blobs = container_client.list_blobs()
    new_blobs = [i.get('name') for i in blobs if is_within_last_minutes(i.get('creation_time'), minutes)]
    if len(blobs_to_download) > 0:
        return
    else:
        raise Exception("No new Data")

if __name__=='__main__':
    authenticate("blob_path", "container_path")