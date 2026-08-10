# Meltano: tap-lightdash -> target-bigquery

Minimal Meltano project that extracts data from Lightdash and loads it into
BigQuery.

## Setup

```bash
cd python/meltano
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in your Lightdash URL/token and GCP project/dataset

meltano install
```

## Run

```bash
meltano run tap-lightdash target-bigquery
```

## Notes

- `TAP_LIGHTDASH_URL` is the base URL of your Lightdash deployment.
- `TAP_LIGHTDASH_PERSONAL_ACCESS_TOKEN` must be a Lightdash personal access
  token (username/password auth is also supported by the tap, but not used
  here).
- `BIGQUERY_PROJECT` / `BIGQUERY_DATASET` control where data lands; the
  dataset is created automatically if it doesn't exist.
- Auth to GCP uses `GOOGLE_APPLICATION_CREDENTIALS` (a service account key)
  or Application Default Credentials (`gcloud auth application-default login`)
  if that variable is left unset.
- `select: ["*.*"]` in `meltano.yml` pulls every stream/field tap-lightdash
  exposes; narrow this once you know which Lightdash objects you need.
