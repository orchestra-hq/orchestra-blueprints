import sys
import dlt
from dlt.sources.rest_api import rest_api_source
from dlt.sources.helpers.rest_client.paginators import PageNumberPaginator

orchestra_api_source = rest_api_source(
    {
        "client": {
            "base_url": f"https://{dlt.config['orchestra_env']}.getorchestra.io/api/engine/public/",
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
            "primary_key": "id",
        },
        "resources": [
            {
                "name": "pipeline_runs",
                "endpoint": {
                    "paginator": PageNumberPaginator(base_page=1),
                },
            },
            {
                "name": "task_runs",
                "endpoint": {
                    "paginator": PageNumberPaginator(base_page=1),
                },
            },
            {
                "name": "operations",
                "endpoint": {
                    "paginator": PageNumberPaginator(base_page=1),
                },
            },
        ],
    }
)


def orchestra_metadata_api_dlt_pipeline(warehouse: str) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="orchestra_metadata_api",
        destination=warehouse,
        dataset_name="orchestra_metadata",
    )
    load_info = pipeline.run(orchestra_api_source)
    print(load_info)


if __name__ == "__main__":
    valid_warehouses = ["bigquery", "mssql", "snowflake"]
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <{'|'.join(valid_warehouses)}>")
        sys.exit(1)

    warehouse = sys.argv[1].lower()
    if warehouse not in valid_warehouses:
        print(
            f"Invalid warehouse: {warehouse}. Valid options are: {', '.join(valid_warehouses)}"
        )
        sys.exit(1)

    orchestra_metadata_api_dlt_pipeline(warehouse)
