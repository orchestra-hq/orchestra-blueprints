"""Regenerate models/snowplow_normalized_events/schema.yml from the generated models.

snowplow_normalize_model_gen.py emits only .sql. Without a matching schema.yml
Lightdash builds no explores for these models (it only surfaces models that have
a YAML definition) and types every column as a string. So this must be re-run
whenever the models are regenerated, or the dashboard silently loses its tables.

Reads the jinja `set` blocks the generator writes into each model, so column
names follow the same rules snowflake__normalize_events uses:
event_id, collector_tstamp, the flat columns verbatim, then each
self-describing field as {alias}_{snakeify_case(key)}.

Usage:  python scripts/gen_schema_yml.py        (from the dbt project root)
"""

import json
import pathlib
import re

MODELS = pathlib.Path("models/snowplow_normalized_events")
LOOKUP = "snowplow_events_normalized"

# Mirrors snowplow_normalize's default__snakeify_case macro.
def snakeify(text: str) -> str:
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    text = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", text)
    return text.replace("-", "_").lower()


def jinja_list(src: str, name: str):
    m = re.search(r"set\s+%s\s*=\s*(\[.*?\])\s*-%%\}" % name, src, re.S)
    return json.loads(m.group(1).replace("'", '"')) if m else None


NUMERIC_FLAT_COLS = {"domain_sessionidx"}
SDE_TYPE_MAP = {
    "string": "varchar", "array": "array", "integer": "number",
    "number": "number", "boolean": "boolean", "object": "variant", "null": "varchar",
}

FRESHNESS = """    config:
      # Rebuild only when EVERY upstream has new data (Orchestra default: any).
      # count/period are required alongside updates_on, and kept at 1 minute on
      # purpose: build_after also suppresses a rebuild if the model was built
      # inside that window, so a longer value would stop a re-run from picking
      # up data you just loaded.
      freshness:
        build_after:
          count: 1
          period: minute
          updates_on: all"""


def column(name: str, data_type: str, description: str) -> list[str]:
    return [f"      - name: {name}",
            f"        data_type: {data_type}",
            f"        description: {description}"]


def main() -> None:
    lines = ["version: 2", "", "models:"]
    for path in sorted(MODELS.glob("*.sql")):
        src, name = path.read_text(), path.stem
        lines.append(f"  - name: {name}")

        if name == LOOKUP:
            lines += [
                "    description: >",
                "      Lookup mapping every modelled event_id to the normalized table it landed in.",
                "      One row per event per destination table. This is the table the summary",
                "      dashboard is built on.",
                FRESHNESS,
                "      meta:",
                "        metrics:",
                "          total_events:",
                "            label: Total events",
                "            type: count_distinct",
                "            sql: event_id",
                "            description: Distinct Snowplow events modelled.",
                "          latest_event_at:",
                "            label: Latest event",
                "            type: max",
                "            sql: collector_tstamp",
                "            description: Collector timestamp of the most recent modelled event.",
                "    data_tests:",
                "      # Warns, never errors: an error fails dbt build, and the Lightdash",
                "      # refresh task is gated on that task succeeding.",
                "      - dbt_utils.recency:",
                "          arguments:",
                "            datepart: day",
                "            field: collector_tstamp",
                "            interval: 3",
                "          config:",
                "            severity: warn",
                "    columns:"]
            lines += column("event_id", "varchar", "Snowplow event UUID.")
            lines += column("collector_tstamp", "timestamp_ntz", "Time the collector received the event.")
            lines += column("event_name", "varchar", "Snowplow event name.")
            lines += column("event_table_name", "varchar", "Normalized table this event was written to.")
            lines += column("unique_id", "varchar", "event_id concatenated with event_table_name.")
            lines.append("")
            continue

        events = jinja_list(src, "event_names") or []
        flat_cols = jinja_list(src, "flat_cols") or []
        sde_keys = jinja_list(src, "sde_keys") or []
        sde_types = jinja_list(src, "sde_types") or []
        sde_aliases = jinja_list(src, "sde_aliases") or []

        lines += ["    description: >",
                  f"      Normalized Snowplow events: {', '.join(events)}.",
                  FRESHNESS,
                  "    columns:"]
        lines += column("event_id", "varchar", "Snowplow event UUID.")
        lines += column("collector_tstamp", "timestamp_ntz", "Time the collector received the event.")
        for col in flat_cols:
            dtype = "number" if col in NUMERIC_FLAT_COLS else "varchar"
            lines += column(col, dtype, f"Atomic events column {col}.")
        for i, keys in enumerate(sde_keys):
            alias = sde_aliases[i] if i < len(sde_aliases) else None
            types = sde_types[i] if i < len(sde_types) else ["string"] * len(keys)
            for key, sde_type in zip(keys, types):
                col = f"{alias}_{snakeify(key)}" if alias else snakeify(key)
                lines += column(col, SDE_TYPE_MAP.get(sde_type, "varchar"),
                                f"Self-describing event field {key} ({sde_type}).")
        lines.append("")

    (MODELS / "schema.yml").write_text("\n".join(lines).rstrip() + "\n")
    print(f"wrote {MODELS / 'schema.yml'}")


if __name__ == "__main__":
    main()
