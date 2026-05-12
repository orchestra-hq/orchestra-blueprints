"""API client and time-range helpers for warehouse savings analysis."""

from datetime import datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_BASE_URL = "https://app.getorchestra.io/api/engine/public"
API_RETRY_TOTAL = 3
API_RETRY_BACKOFF_FACTOR = 1
API_RETRY_STATUS_FORCELIST = [429, 500, 502, 503, 504]
DEFAULT_ANALYSIS_DAYS = 30
INTEGRATION_TYPE = "DBT_CORE"


class OrchestraAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=API_RETRY_TOTAL,
                backoff_factor=API_RETRY_BACKOFF_FACTOR,
                status_forcelist=API_RETRY_STATUS_FORCELIST,
            )
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    def _get_all_pages(self, endpoint: str, params: dict) -> list[dict]:
        all_results = []
        page = 1

        while True:
            params["page"] = page
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            all_results.extend(data.get("results", []))

            total = data.get("total", 0)
            if len(all_results) >= total or len(data.get("results", [])) == 0:
                break

            page += 1

        return all_results

    def _format_datetime_for_api(self, dt: datetime) -> str:
        iso_str = dt.isoformat()
        if iso_str.endswith("+00:00") or iso_str.endswith("-00:00"):
            return iso_str[:-6] + "Z"
        if "+" in iso_str or (len(iso_str) >= 6 and iso_str[-6] in "+-"):
            return iso_str
        return iso_str + "Z"

    def _chunk_time_range(
        self,
        time_from: datetime,
        time_to: datetime,
    ) -> list[tuple[datetime, datetime]]:
        chunks = []
        current_to = time_to

        while current_to > time_from:
            current_from = max(time_from, current_to - timedelta(days=7))
            chunks.append((current_from, current_to))
            current_to = current_from - timedelta(seconds=1)

        return chunks

    def get_operations(
        self,
        time_from: datetime,
        time_to: datetime,
    ) -> list[dict]:
        all_results = []

        chunks = self._chunk_time_range(time_from, time_to)
        print(f"   Splitting time range into {len(chunks)} chunks of 7 days each...")

        for i, (chunk_from, chunk_to) in enumerate(chunks, 1):
            print(
                f"   Fetching chunk {i}/{len(chunks)}: "
                f"{chunk_from.date()} to {chunk_to.date()}",
            )
            chunk_results = self._get_all_pages(
                "/operations",
                {
                    "time_from": self._format_datetime_for_api(chunk_from),
                    "time_to": self._format_datetime_for_api(chunk_to),
                    "integration": INTEGRATION_TYPE,
                },
            )
            all_results.extend(chunk_results)

        return all_results

    def get_task_runs(
        self,
        time_from: datetime,
        time_to: datetime,
    ) -> list[dict]:
        all_results = []

        chunks = self._chunk_time_range(time_from, time_to)
        print(f"   Splitting time range into {len(chunks)} chunks of 7 days each...")

        for i, (chunk_from, chunk_to) in enumerate(chunks, 1):
            print(
                f"   Fetching chunk {i}/{len(chunks)}: "
                f"{chunk_from.date()} to {chunk_to.date()}",
            )
            chunk_results = self._get_all_pages(
                "/task_runs",
                {
                    "time_from": self._format_datetime_for_api(chunk_from),
                    "time_to": self._format_datetime_for_api(chunk_to),
                    "integration": INTEGRATION_TYPE,
                },
            )
            all_results.extend(chunk_results)

        return all_results


def calculate_time_range(
    days: int = DEFAULT_ANALYSIS_DAYS,
) -> tuple[datetime, datetime]:
    time_to = datetime.now(timezone.utc)
    time_from = time_to - timedelta(days=days)
    return time_from, time_to
