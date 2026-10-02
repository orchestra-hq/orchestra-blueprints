# Store sales chart -> Slack

Reads the store-sales workbook from S3, aggregates daily units by city, renders a
line chart, and posts it to Slack as an `image` block backed by a presigned S3 URL.

Run by the Orchestra pipeline **Store sales chart to Slack**.

## Why a presigned URL rather than `files.upload`

The Slack app has `chat:write` but not `files:write`, so it cannot upload a file.
The chart is written to `s3://<bucket>/charts/` and shared as a SigV4 presigned GET
URL, which Slack fetches and proxies onto its own CDN. Nothing is made public and no
bucket policy is changed. The URL is signed for 7 days (the SigV4 maximum); each
scheduled run mints a fresh one, so the expiry never bites on a recurring schedule.

Granting the Slack app `files:write` would let this post the PNG directly - a
simplification worth making if the app's scopes are ever revisited.

## Configuration

Secrets, set on the Orchestra **Python connection** (never on the task):

| Key | Value |
|---|---|
| `S3_ACCESS_KEY_ID` | access key for the S3 bucket |
| `S3_SECRET_ACCESS_KEY` | matching secret key |
| `SLACK_BOT_TOKEN` | Slack bot token with `chat:write` |

Non-secret settings, set as task environment variables:

| Key | Default |
|---|---|
| `S3_REGION` | `eu-west-2` |
| `S3_BUCKET` | `orchestra-demo-account` |
| `S3_SOURCE_KEY` | `vape_data_test/Vape Data.xlsx` |
| `S3_CHART_PREFIX` | `charts` |
| `SLACK_CHANNEL` | Slack channel ID |

## Notes

* Only `matplotlib` is a third-party dependency. S3 request signing and the `.xlsx`
  reader are written against the standard library, so there is no `boto3`/`openpyxl`.
* The workbook writes each city label only on the first row of its block, so the
  parser forward-fills it. Without that, only one store per city is summed and the
  totals come out ~6x too low.
* Chart colours are categorical slots 1-2 of the validated default palette
  (blue `#2a78d6`, orange `#eb6834`) on the light surface.
