import os
from unittest import mock
import paramiko
import requests
import json
import boto3
import datetime
import time



def upload_file_to_s3(file_location,bucket_name,key):
    s3 = boto3.client('s3')
    output = s3.upload_file(file_location,bucket_name,key)
    print(output)

def list_s3_objects(bucket_name):
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(bucket_name)
    for my_bucket_object in my_bucket.objects.all():
        print(my_bucket_object)
        

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

def connect_sftp(host, port, username, password):
    """Establish and return a mocked SFTP connection"""
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return sftp, transport

def list_files(sftp, remote_dir):
    """List all files in the given remote directory"""
    try:
        files = sftp.listdir(remote_dir)
        print(f"Files in '{remote_dir}':")
        for f in files:
            print(f" - {f}")
        return files
    except FileNotFoundError:
        print(f"Directory not found: {remote_dir}")
        return []

def download_file(sftp, remote_path, local_path):
    """Download a file from the remote path to the local path"""
    try:
        with sftp.open(remote_path, 'r') as remote_file:
            content = remote_file.read()
        with open(local_path, 'wb') as f:
            f.write(content)
        print(f"Downloaded: {remote_path} → {local_path}")
    except FileNotFoundError:
        print(f"File not found: {remote_path}")

def mock_sftp():
    # ==== CONFIGURATION ====
    host = "mock_host"
    port = 22
    username = "mock_user"
    password = "mock_pass"
    remote_directory = "/mock/remote"
    file_to_download = os.getenv('FILE_PATH') 
    local_download_path = os.path.join(os.getcwd(), file_to_download)

    # ==== MOCKING START ====
    with mock.patch('paramiko.Transport') as MockTransport, \
         mock.patch('paramiko.SFTPClient.from_transport') as MockSFTPClient:

        mock_transport_instance = mock.MagicMock()
        MockTransport.return_value = mock_transport_instance

        mock_sftp_instance = mock.MagicMock()
        MockSFTPClient.return_value = mock_sftp_instance

        # Mock listdir return
        mock_sftp_instance.listdir.return_value = ["shipments.json", "another_file.csv"]

        # Mock file reading — JSON with sample shipment data
        mock_shipments_data = {
            "shipments": [
                {"id": "SHP001", "origin": "New York", "destination": "Chicago", "status": "In Transit"},
                {"id": "SHP002", "origin": "Los Angeles", "destination": "San Francisco", "status": "Delivered"},
                {"id": "SHP003", "origin": "Miami", "destination": "Houston", "status": "Pending"}
            ]
        }
        json_bytes = json.dumps(mock_shipments_data, indent=2).encode('utf-8')

        mock_file = mock.MagicMock()
        mock_file.read.return_value = json_bytes
        mock_sftp_instance.open.return_value.__enter__.return_value = mock_file

        try:
            # Connect (mocked)
            sftp, transport = connect_sftp(host, port, username, password)

            # 1. List files (mocked)
            list_files(sftp, remote_directory)

            # 2. Download file (mocked read and local write)
            full_remote_path = f"{remote_directory}/{file_to_download}"
            print("Fetching file from: " + str(full_remote_path))
            download_file(sftp, full_remote_path, local_download_path)
            print("Downloading File Complete")
            date__ = str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d'))
            filename = "sftp/"+date__+"/"+date__+os.getenv('FILE_PATH')
            #upload_file_to_s3(os.getenv('FILE_PATH'), os.getenv('S3_BUCKET'), filename)
            upload_file_to_s3(os.getenv('FILE_PATH'), "orchestra-snowflake", filename)
            print("File uploaded to S3")
            # Clean up (mocked)
            sftp.close()
            transport.close()

            # Output S3-style mock path
            #set_orchestra_output("s3_path", filename)
            
        except Exception as e:
            #set_orchestra_output("error", str(e))
            print(f"Error: {e}")

if __name__ == "__main__":
    mock_sftp()