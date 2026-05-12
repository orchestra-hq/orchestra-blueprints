import json
import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class RuntimeInputs:
    source: str | None
    object_name: str | None
    params: str | None
    destination: str | None
    source_creds: str | None
    dest_creds: str | None

    @classmethod
    def from_env(cls) -> "RuntimeInputs":
        return cls(
            source=os.getenv("SOURCE"),  # Set in Orchestra Pipeline Task
            object_name=os.getenv("OBJECT"),  # Set in Orchestra Pipeline Task
            params=os.getenv("PARAMS"),  # Set in Orchestra Pipeline Task
            destination=os.getenv("DESTINATION"),  # Set in Orchestra Pipeline Task
            source_creds=os.getenv(
                "SOURCE_CREDS"
            ),  # Set in Orchestra Python Connection
            dest_creds=os.getenv("DEST_CREDS"),  # Set in Orchestra Python Connection
        )


def connect_to_source() -> None:
    pass


def connect_to_destination() -> None:
    pass


def ingest_data_from_source(
    source: str | None,
    object_name: str | None,
    params: str | None,
    source_creds: str | None,
) -> dict[str, Any]:
    return {}


def move_data_to_destination(
    data: dict[str, Any], params: str | None, dest: str | None, dest_creds: str | None
) -> None:
    pass


def move_data() -> None:
    try:
        runtime = RuntimeInputs.from_env()
        data = ingest_data_from_source(
            runtime.source, runtime.object_name, runtime.params, runtime.source_creds
        )
        move_data_to_destination(
            data, runtime.params, runtime.destination, runtime.dest_creds
        )
    except Exception as e:
        raise Exception("Pipeline did not complete due to: " + str(e))


def set_orchestra_output(output_name: str, output_value: str) -> None:
    """
    Use this function to set an output on the Task Run that can be used by downstream tasks
    """
    data = {
        "event_type": "SET_OUTPUT",
        "task_run_id": os.getenv("ORCHESTRA_TASK_RUN_ID"),  # Set Automatically
        "output_name": output_name,
        "output_value": output_value,
    }

    url = "https://webhook.getorchestra.io"
    api_key = os.getenv("ORCHESTRA_API_KEY")  # Set in Orchestra Python Connection
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    # Print the response
    print(response.status_code)
    print(response.text)
    if response.status_code != 200:
        raise Exception("")


if __name__ == "__main__":
    print("Hello, World!")
