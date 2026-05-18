# Run Multiple Pipelines (Orchestra Platform Pattern)

This is an **Orchestra-as-a-platform** pattern: it runs Orchestra pipelines via
the Orchestra API using a JSON config file, then prints a success/failure
summary.

It is not designed to be invoked as a single task module by Orchestra during a
pipeline run. Instead, use it as a helper to orchestrate (or audit) other
pipelines programmatically.

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a config JSON (see `example.config.json`) and run:

```bash
python run_multiple_pipelines.py --config path/to/config.json --env .env
```

