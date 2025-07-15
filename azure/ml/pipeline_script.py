from azureml.core import Workspace, Experiment, Environment, ScriptRunConfig
from azureml.data import OutputFileDatasetConfig
from azureml.pipeline.core import Pipeline, PipelineData
from azureml.pipeline.steps import PythonScriptStep
from azureml.core.compute import ComputeTarget, AmlCompute

# 1. Connect to the Azure ML workspace
ws = Workspace.from_config()

# 2. Set up the compute target
compute_name = "your-compute-cluster"
compute_target = ComputeTarget(workspace=ws, name=compute_name)

# 3. Define pipeline data (intermediate output between steps)
output_data = PipelineData(name="prepared_data", datastore=ws.get_default_datastore())

# 4. Define environments
env = Environment.get(ws, name="AzureML-sklearn-1.0-ubuntu20.04-py38-cpu")

# 5. Define data preparation step
prep_step = PythonScriptStep(
    name="Prep Data",
    script_name="prep_data.py",  # Your script file
    arguments=["--output_path", output_data],
    outputs=[output_data],
    compute_target=compute_target,
    source_directory="./scripts",  # Folder where your script is
    runconfig=ScriptRunConfig(source_directory="./scripts", environment=env).run_config,
    allow_reuse=True
)

# 6. Define training step
train_step = PythonScriptStep(
    name="Train Model",
    script_name="train.py",
    arguments=["--input_path", output_data],
    inputs=[output_data],
    compute_target=compute_target,
    source_directory="./scripts",
    runconfig=ScriptRunConfig(source_directory="./scripts", environment=env).run_config,
    allow_reuse=True
)

# 7. Create pipeline and experiment
pipeline = Pipeline(workspace=ws, steps=[prep_step, train_step])
experiment = Experiment(workspace=ws, name="ml-pipeline-demo")

# 8. Submit pipeline
pipeline_run = experiment.submit(pipeline)
pipeline_run.wait_for_completion(show_output=True)
