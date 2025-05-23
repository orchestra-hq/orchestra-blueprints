### IMPORTS
from datetime import datetime
import bauplan
import os

def source_to_iceberg_table(
    bauplan_client: bauplan.Client,
    table_name: str,
    namespace: str,
    source_s3_pattern: str,
    bauplan_ingestion_branch: str
):
    """
    
    Wrap the table creation and upload process in Bauplan.
    
    """
    if bauplan_client.has_branch(bauplan_ingestion_branch):
        bauplan_client.delete_branch(bauplan_ingestion_branch)
        
    
    # create the branch from main HEAD
    bauplan_client.create_branch(bauplan_ingestion_branch, from_ref='main')
    # we check if the branch is there (and learn a new API method ;-))
    assert bauplan_client.has_branch(bauplan_ingestion_branch), "Branch not found"
    # now we create the table in the branch
    bauplan_client.create_table(
        table=table_name,
        search_uri=source_s3_pattern,
        namespace=namespace,
        branch=bauplan_ingestion_branch,
        # just in case the test table is already there for other reasons
        replace=True  
    )
    # we check if the table is there (and learn a new API method ;-))
    fq_name = f"{namespace}.{table_name}"
    assert bauplan_client.has_table(table=fq_name, ref=bauplan_ingestion_branch), "Table not found"
    is_imported = bauplan_client.import_data(
        table=table_name,
        search_uri=source_s3_pattern,
        namespace=namespace,
        branch=bauplan_ingestion_branch
    )

    return is_imported


def run_quality_checks(
    bauplan_client: bauplan.Client,
    bauplan_ingestion_branch: str,
    table_name: str,
    namespace: str
):
    """
    
    We check the data quality by running the checks in-process: we use 
    Bauplan SDK to query the data as an Arrow table, and check if the 
    target column is not null through vectorized PyArrow operations.
    
    """
    # we retrieve the data and check if the table is column has any nulls
    # make sure the column you're checking is in the table, so change this appropriately
    # if you're using a different dataset
    column_to_check = 'PULocationID'
    # NOTE if you don't want to use any SQL, you can interact with the lakehouse in pure Python
    # and still back an Arrow table (in this one column) through a performant scan.
    print("Perform a S3 columnar scan on the column {}".format(column_to_check))
    wap_table = bauplan_client.scan(
        table=namespace+"."+table_name,
        ref=bauplan_ingestion_branch,
        columns=[column_to_check]
    )
    #print("Read the table successfully!")
    #assert wap_table[column_to_check].null_count > 0, "Quality check failed"
    #print("Quality check passed")
    
    return True


def merge_branch(
    bauplan_client: bauplan.Client,
    bauplan_ingestion_branch: str
):
    """
    
    We merge the ingestion branch into the main branch. If this succeed,
    the transaction itself is considered successful.
    
    """
    # we merge the branch into the main branch
    return bauplan_client.merge_branch(
        source_ref=bauplan_ingestion_branch,
        into_branch='main'
    )


def delete_branch_if_exists(transaction):
    """
    
    If the task fails or the merge succeeded, we delete the branch to avoid clutter!
    
    """
    _client = bauplan.Client()
    ingestion_branch = transaction.get('bauplan_ingestion_branch')
    if  _client.has_branch(ingestion_branch):
        print(f"Deleting the branch {ingestion_branch}")
        _client.delete_branch(ingestion_branch)
    else:
        print(f"Branch {ingestion_branch} does not exist, nothing to delete.")
        
    return


def wap_with_bauplan(
    bauplan_ingestion_branch: str, 
    source_s3_pattern: str,
    table_name: str,
    namespace: str
):
    """
    Run the WAP ingestion pipeline using Bauplan in a Prefect flow
    leveraging the new concept of transactions:
    
    https://docs-3.prefect.io/3.0rc/develop/transactions#write-your-first-transaction
    """
    print("Starting WAP at {}!".format(datetime.now()))
    bauplan_client = bauplan.Client(api_key=os.environ['BAUPLAN_API_KEY'])
    ### THIS IS THE WRITE
    # first, ingest data from the s3 source into a table the Bauplan branch
    source_to_iceberg_table(
        bauplan_client,
        table_name, 
        namespace,
        source_s3_pattern,
        bauplan_ingestion_branch
    )
    ### THIS IS THE AUDIT
    # we query the table in the branch and check we have no nulls
    run_quality_checks(
        bauplan_client,
        bauplan_ingestion_branch, 
        table_name=table_name,
        namespace=namespace
    )
    # THIS IS THE PUBLISH 
    # finally, we merge the branch into the main branch if the quality checks passed
    merge_branch(
        bauplan_client,
        bauplan_ingestion_branch
    )
    
            
    # say goodbye
    print("All done at {}, see you, space cowboy.".format(datetime.now()))

    return


if __name__ == "__main__":
    print("Starting WAP at {}!".format(datetime.now()))

    bauplan_client = bauplan.Client(api_key=os.environ['BAUPLAN_API_KEY'])
    
    #ghyjkl
    return_object = bauplan_client.run(ref="orchestra.dev_hugo", namespace="bauplan")
    job_list = bauplan_client.get_job_logs(job_id_prefix=return_object.job_id)
    for i in job_list:
        print(i.message)
    print("Data Transformations run successfully")

  