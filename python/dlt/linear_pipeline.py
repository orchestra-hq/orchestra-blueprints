"""Run the Linear -> MotherDuck dlt pipeline.

Environment variables consumed:
    LINEAR_API_KEY        Linear personal API key.
    MOTHERDUCK_API_TOKEN  MotherDuck service token (alias of MOTHERDUCK_TOKEN).
    LINEAR_SINCE_DAYS     Lookback window in days for ``updatedAt`` (default 7).
    LINEAR_MD_DATABASE    Target MotherDuck database (default ``my_db``).
"""

import os

import dlt

from linear import linear_source


def _configure_motherduck_credentials() -> None:
    """Translate MOTHERDUCK_API_TOKEN into the form dlt's destination expects."""
    token = os.environ.get("MOTHERDUCK_API_TOKEN") or os.environ.get(
        "MOTHERDUCK_TOKEN"
    )
    if not token:
        raise EnvironmentError(
            "MOTHERDUCK_API_TOKEN (or MOTHERDUCK_TOKEN) must be set."
        )
    os.environ.setdefault("MOTHERDUCK_TOKEN", token)
    database = os.environ.get("LINEAR_MD_DATABASE", "my_db")
    os.environ["DESTINATION__MOTHERDUCK__CREDENTIALS"] = (
        f"md:{database}?motherduck_token={token}"
    )


def run_pipeline(since_days: int = 7) -> None:
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        raise EnvironmentError("LINEAR_API_KEY must be set.")

    _configure_motherduck_credentials()

    pipeline = dlt.pipeline(
        pipeline_name="linear",
        dataset_name="dlt_linear",
        destination="motherduck",
    )

    source = linear_source(api_key=api_key, since_days=since_days)
    info = pipeline.run(source)
    print(info)


if __name__ == "__main__":
    days = int(os.getenv("LINEAR_SINCE_DAYS", "7"))
    run_pipeline(since_days=days)
