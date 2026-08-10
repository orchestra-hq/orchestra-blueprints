# Meltano: tap-hubspot -> target-bigquery

Minimal Meltano project that extracts data from HubSpot and loads it into
BigQuery.

## Setup

```bash
cd meltano
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in your HubSpot token and GCP project/dataset

meltano install
```

## Run

```bash
meltano run tap-hubspot target-bigquery
```

## Notes

- `TAP_HUBSPOT_ACCESS_TOKEN` must be a HubSpot private app access token.
- `BIGQUERY_PROJECT` / `BIGQUERY_DATASET` control where data lands; the
  dataset is created automatically if it doesn't exist.
- Auth to GCP uses `GOOGLE_APPLICATION_CREDENTIALS` (a service account key)
  or Application Default Credentials (`gcloud auth application-default login`)
  if that variable is left unset.
- `select: ["*.*"]` in `meltano.yml` pulls every stream/field tap-hubspot
  exposes; narrow this once you know which HubSpot objects you need.
