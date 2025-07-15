import argparse
import pandas as pd
from azureml.core import Run

parser = argparse.ArgumentParser()
parser.add_argument("--output_path", type=str)
args = parser.parse_args()

run = Run.get_context()

# Dummy data
df = pd.DataFrame({
    "feature1": [1, 2, 3],
    "feature2": [4, 5, 6],
    "label": [0, 1, 0]
})

# Save to output
output_path = args.output_path
df.to_csv(output_path + "/data.csv", index=False)
print("Prepping data complete")
