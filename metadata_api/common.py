import requests
import os

API_URL = "https://app.getorchestra.io/api/engine/public/{resource}/"
COLUMNS = {
    "operations": [
        "id",
        "name",
    ],
    "pipeline_runs": [
        "id",
        "name",
        "status",
        "created_at",
        "updated_at",
    ],
    "task_runs": [
        "id",
        "name",
    ],
}
VALID_RESOURCES = [
    "operations",
    "pipeline_runs",
    "task_runs",
]


def fetch_data_from_api(resource: str) -> list[dict]:
    print(f"Fetching data from API for '{resource}'...")
    api_token = os.environ.get("ORCHESTRA_API_TOKEN")
    if not api_token:
        raise ValueError("ORCHESTRA_API_TOKEN environment variable is not set.")
    response = requests.get(
        API_URL.format(resource=resource),
        headers={"Authorization": f"Bearer {api_token}"},
    )
    response.raise_for_status()
    return response.json()


def parse_record_values(records: list[dict], resource: str) -> list:
    values = []
    for item in records:
        value = {}
        for column in COLUMNS[resource]:
            value[column] = item.get(column)
        values.append(value)
    return values
