import argparse
import pandas as pd
from azureml.core import Run

parser = argparse.ArgumentParser()
parser.add_argument("--input_path", type=str)
args = parser.parse_args()

run = Run.get_context()

# Load data
df = pd.read_csv(args.input_path + "/data.csv")

# Dummy model logic
print("Training model on data:")
print(df.head())

run.complete()
