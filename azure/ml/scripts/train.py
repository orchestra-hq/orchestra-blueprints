import time
import random
import datetime


class LogStyle:
    INFO = "\033[94m[INFO]\033[0m"
    SUCCESS = "\033[92m[SUCCESS]\033[0m"
    WARNING = "\033[93m[WARNING]\033[0m"
    ERROR = "\033[91m[ERROR]\033[0m"
    RESET = "\033[0m"


def log(msg, level=LogStyle.INFO):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{level} {timestamp} - {msg}")


class MockAzureMLWorkspace:
    def __init__(self, name, subscription_id, resource_group):
        self.name = name
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        log(f"Connected to Azure ML Workspace: {self.name}")

    def register_model(self, model_name, model_path):
        log(f"Registering model '{model_name}' from path '{model_path}'")
        model_id = f"{model_name}:{random.randint(1, 100)}"
        log(f"Model registered with ID: {model_id}", LogStyle.SUCCESS)
        return model_id

    def submit_experiment(self, experiment_name, script):
        log(f"Submitting experiment '{experiment_name}' using script '{script}'")
        run_id = f"run_{random.randint(1000, 9999)}"
        log(f"Experiment submitted. Run ID: {run_id}", LogStyle.SUCCESS)
        return run_id

    def monitor_run(self, run_id):
        log(f"Monitoring run: {run_id}")
        for epoch in range(1, 6):
            time.sleep(1)
            loss = round(random.uniform(0.4, 0.9) / epoch, 4)
            acc = round(random.uniform(0.6, 0.99), 4)
            log(f"[Epoch {epoch}/5] Loss: {loss} | Accuracy: {acc}")
        log("Run completed successfully ✅", LogStyle.SUCCESS)

    def deploy_model(self, model_id, service_name):
        log(f"Deploying model '{model_id}' as web service '{service_name}'")
        endpoint = f"https://{service_name}.azurewebsites.net/score"
        time.sleep(1)
        log("Validating deployment artifacts...")
        time.sleep(1)
        log("Allocating compute resources...")
        time.sleep(1)
        log(f"Model deployed to endpoint: {endpoint}", LogStyle.SUCCESS)
        return endpoint

    def run_inference(self, endpoint, input_data):
        log(f"Calling model endpoint: {endpoint}")
        log(f"Input: {input_data}")
        simulated_output = {
            "prediction": random.choice(["cat", "dog", "chicken", "robot"]),
            "confidence": round(random.uniform(0.8, 0.99), 4)
        }
        time.sleep(1)
        log(f"Output: {simulated_output}", LogStyle.SUCCESS)
        return simulated_output


# Usage Example (Mocks Only)
if __name__ == "__main__":
    workspace = MockAzureMLWorkspace(
        name="my-ml-workspace",
        subscription_id="1234-5678-9012",
        resource_group="my-resource-group"
    )

    model_id = workspace.register_model("image_classifier", "./models/image_classifier.pkl")
    run_id = workspace.submit_experiment("train_classifier", "train_classifier.py")
    workspace.monitor_run(run_id)
    endpoint = workspace.deploy_model(model_id, "image-service")
    output = workspace.run_inference(endpoint, {"image_url": "https://example.com/cat.jpg"})

    log("All operations completed (mocked)", LogStyle.SUCCESS)
