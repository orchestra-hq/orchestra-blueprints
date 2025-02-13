import datetime
import logging
import azure.functions as func
from azure.storage.filedatalake import DataLakeServiceClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import requests
import os

def get_blob_service_client(blob_accnt_name):
    _blob_acct_url = f'https://{blob_accnt_name}.blob.core.windows.net'
    token_credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=_blob_acct_url, credential=token_credential)

def get_container_client(blob_client: BlobServiceClient, container: str):
    return blob_client.get_container_client(container)

def is_within_last_hour(dt, hours):
    now = datetime.datetime.now(dt.tzinfo)  # Ensure timezone compatibility
    one_hour_ago = now - datetime.timedelta(hours=hours)
    return one_hour_ago <= dt <= now

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    account_name = 'your_account_name'  # Define your account name
    blob_path = 'your_blob_path'
    container_path = 'your_container_name'
    duration_hours = 1
    pipeline_id = 'your_pipeline_id'

    blob_client = get_blob_service_client(account_name)
    container_client = get_container_client(blob_client, container_path)
    blobs = container_client.list_blobs()
    blobs_to_download = [blob.name for blob in blobs if is_within_last_hour(blob.creation_time, duration_hours)]

    logging.info(f'Files to download: {blobs_to_download}')

    if len(blobs_to_download) > 0:
        orchestra_token = os.getenv('ORCHESTRA_TOKEN')
        url = f"https://app.getorchestra.io/engine/public/pipelines/{pipeline_id}/start"
        headers = {'Authorization': f'Bearer {orchestra_token}'}
        response = requests.post(url, headers=headers)
        logging.info(f'Pipeline triggered: {response.status_code}')
    else:
        logging.error("No file found in the last hour.")

