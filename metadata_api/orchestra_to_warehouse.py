import dlt
from dlt.sources.rest_api import rest_api_source
from dlt.sources.helpers.rest_client.paginators import PageNumberPaginator


orchestra_api_source = rest_api_source(
    {
        "client": {
            "base_url": "https://dev.getorchestra.io/api/engine/public/",
            "auth": {
                "type": "bearer",
                "token": dlt.secrets["orchestra_api_token"],
            },
        },
        "resource_defaults": {
            "write_disposition": "merge",
            "endpoint": {
                "params": {
                    "page_size": 100,
                },
            },
        },
        "resources": [
            {
                "name": "pipeline_runs",
                "endpoint": {
                    "path": "pipeline_runs/",
                    "paginator": PageNumberPaginator(base_page=1),
                    "params": {
                        "time_from": "{incremental.start_value}",
                    },
                    "incremental": {
                        "cursor_path": "createdAt",
                        "initial_value": "2025-04-24",
                    },
                },
                "primary_key": "id",
            }
        ],
    }
)


def orchestra_metadata_api_dlt_pipeline() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="orchestra_metadata_api",
        destination="snowflake",  # could be bigquery
        dataset_name="orchestra_metadata",
    )
    load_info = pipeline.run(orchestra_api_source)
    print(load_info)


if __name__ == "__main__":
    orchestra_metadata_api_dlt_pipeline()
