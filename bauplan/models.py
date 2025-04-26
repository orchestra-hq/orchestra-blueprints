"""

This script collects Bauplan models, i.e. transformations that are run in Python mapping an
input table (data=bauplan.Model), to another table (a dataframe-like object we return).

Note that collecting models in a single file called models.py is not required, but we find it useful
to keep the pipeline code together.

"""

# import bauplan to get the decorators available
import bauplan

# this decorator tells Bauplan that this function has the model semantics - input: table, output: table.
# the input is always an Arrow table, output can be an Arrow table, a pandas dataframe or a list of dictionaries.
# the materialize flag is used to tell the system whether to persist the output of a function as an Iceberg table in the data catalog
@bauplan.model()
# this decorator allow you to specify the Python version and any pip packages you need for this function
# remember that the environment for each function is entirely separated
# e.g. different functions can run with different packages, different versions of the same packages
# and/or even different versions of the python interpreter
@bauplan.python('3.11')
def trips_and_zones_2(
        trips=bauplan.Model(
            'taxi_fhvhv',
            # this function performs an S3 scan directly in Python, so we can specify the columns and the filter pushdown
            # by pushing the filters down to S3 we make the system considerably more performant
            columns=[
                'pickup_datetime',
                'dropoff_datetime',
                'PULocationID',
                'DOLocationID',
                'trip_miles',
                'trip_time',
                'base_passenger_fare',
                'tolls',
                'sales_tax',
                'tips',
                ],
            filter="pickup_datetime >= '2022-12-15T00:00:00-05:00' AND pickup_datetime < '2023-01-01T00:00:00-05:00'"
        ),
        zones=bauplan.Model(
            'taxi_zones',
        ),
):
    # the following code is PyArrow https://arrow.apache.org/docs/python/index.html
    # because Bauplan speaks Arrow natively you don't need to import PyArrow explicitly

    # join 'trips' with 'zones' on 'PULocationID'
    pickup_location_table = trips.join(zones, 'PULocationID', 'LocationID').combine_chunks()
    return pickup_location_table


@bauplan.model()
# this time notice that we specify one dependency, namely Pandas 2.2.0.
@bauplan.python('3.11', pip={'pandas': '1.5.3', 'numpy': '1.23.2'})
def normalized_taxi_trips(
        data=bauplan.Model(
            # this function takes the previous one 'trips_and_zones' as an input
            # functions are chained together to form a DAG by naming convention
            'trips_and_zones_2',
        )
):
    import pandas as pd
    import numpy as np
    import math

    # print some debug info - you will see every print statement directly in your terminal
    size_in_gb = round(data.nbytes / math.pow(1024, 3), 3)
    print(f"\nThis table is {size_in_gb} GB and has {data.num_rows} rows\n")

    # convert data from Arrow to Pandas
    df = data.to_pandas()
    # create time filter on datetime UTC
    time_filter = pd.to_datetime('2022-01-01')
    time_filter_utc = time_filter.tz_localize('UTC')
    # filter df by timestamp
    df = df[df['pickup_datetime'] >= time_filter_utc]
    # exclude rows with trip_miles = 0
    df = df[df['trip_miles'] > 0.0]
    # exclude rows with trip_miles > 200
    df = df[df['trip_miles'] < 200.0]
    # create a new columns with log-transformed trip_miles to better model skewed distribution
    df['log_trip_miles'] = np.log10(df['trip_miles'])

    # return a Pandas dataframe
    return df
