from typing import List
import dlt

from hubspot import hubspot, hubspot_events_for_objects, THubspotObjectType
from setup_logger import build_logger




logger = build_logger("debug.log")
def run_pipeline() -> None:
    """
    This function loads all resources from HubSpot CRM

    Returns:
        None
    """
    logger.info("Starting to run dlt Pipeline")
    # Create a DLT pipeline object with the pipeline name, dataset name, and destination database type
    # Add dev_mode=(True or False) if you need your pipeline to create the dataset in your destination
    p = dlt.pipeline(
        pipeline_name="hubspot",
        dataset_name="dlt_hubspot",
        destination='bigquery',
    )

    data = hubspot()
    data.companies.bind(props=['hs_time_in_opportunity', 'hs_analytics_first_visit_timestamp'])

    # Run the pipeline with the HubSpot source connector
    info = p.run(data)

    # Print information about the pipeline run
    print(info)
    logger.info("Completed Loading Data from Hubspot to BigQuery")


def load_crm_data_with_history() -> None:
    """
    Loads all HubSpot CRM resources and property change history for each entity.
    The history entries are loaded to a tables per resource `{resource_name}_property_history`, e.g. `contacts_property_history`

    Returns:
        None
    """

    # Create a DLT pipeline object with the pipeline name, dataset name, and destination database type
    # Add dev_mode=(True or False) if you need your pipeline to create the dataset in your destination
    p = dlt.pipeline(
        pipeline_name="hubspot",
        dataset_name="hubspot_dataset",
        destination='bigquery',
    )

    # Configure the source with `include_history` to enable property history load, history is disabled by default
    data = hubspot(include_history=True)
    data.contacts.bind()
    # Run the pipeline with the HubSpot source connector
    info = p.run(data)

    # Print information about the pipeline run
    print(info)


def load_crm_objects_with_custom_properties() -> None:
    """
    Loads CRM objects, reading only properties defined by the user.
    """

    # Create a DLT pipeline object with the pipeline name,
    # dataset name, properties to read and destination database
    # type Add dev_mode=(True or False) if you need your
    # pipeline to create the dataset in your destination
    p = dlt.pipeline(
        pipeline_name="hubspot",
        dataset_name="hubspot_dataset",
        destination='bigquery',
    )

    source = hubspot()

    # By default, all the custom properties of a CRM object are extracted,
    # ignoring those driven by Hubspot (prefixed with `hs_`).

    # To read fields in addition to the custom ones:
    # source.contacts.bind(props=["date_of_birth", "degree"])

    # To read only two particular fields:
    source.contacts.bind(props=["date_of_birth", "degree"], include_custom_props=False)

    # Run the pipeline with the HubSpot source connector
    info = p.run(source)

    # Print information about the pipeline run
    print(info)


def load_web_analytics_events(
    object_type: THubspotObjectType, object_ids: List[str]
) -> None:
    """
    This function loads web analytics events for a list objects in `object_ids` of type `object_type`

    Returns:
        None
    """

    # Create a DLT pipeline object with the pipeline name, dataset name, and destination database type
    p = dlt.pipeline(
        pipeline_name="hubspot",
        dataset_name="hubspot_dataset",
        destination='bigquery',
        dev_mode=False,
    )

    # you can get many resources by calling this function for various object types
    resource = hubspot_events_for_objects(object_type, object_ids)
    # and load them together passing resources in the list
    info = p.run([resource])

    # Print information about the pipeline run
    print(info)

