import os
from datetime import datetime, timedelta, timezone

import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.lines import Line2D
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ORCHESTRA_API_KEY = os.getenv("ORCHESTRA_API_KEY")

# API Configuration
API_BASE_URL = "https://app.getorchestra.io/api/engine/public"
API_RETRY_TOTAL = 3
API_RETRY_BACKOFF_FACTOR = 1
API_RETRY_STATUS_FORCELIST = [429, 500, 502, 503, 504]

# Data Configuration
DEFAULT_ANALYSIS_DAYS = 30
INTEGRATION_TYPE = "DBT_CORE"

# Plot Configuration
FIGURE_WIDTH = 14
FIGURE_HEIGHT = 10
PLOT_HEIGHT_RATIO = 2.5
TABLE_HEIGHT_RATIO = 1
LINE_WIDTH = 1.5
LINE_ALPHA = 0.8
MARKER_SIZE = 4
FIRST_USE_MARKER_SIZE = 300
GRID_ALPHA = 0.3
TITLE_FONTSIZE = 14
AXIS_LABEL_FONTSIZE = 12
LEGEND_FONTSIZE = 9
TABLE_FONTSIZE = 9
TABLE_SCALE_Y = 2

# Color Configuration
COLOR_PALETTE = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # olive
    "#17becf",  # cyan
]
FIRST_USE_MARKER_COLOR = "gold"
FIRST_USE_MARKER_EDGE_COLOR = "black"
FIRST_USE_MARKER_EDGE_WIDTH = 1.5

plt.rcParams["figure.figsize"] = (FIGURE_WIDTH, FIGURE_HEIGHT)


class OrchestraAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=API_RETRY_TOTAL,
                backoff_factor=API_RETRY_BACKOFF_FACTOR,
                status_forcelist=API_RETRY_STATUS_FORCELIST,
            )
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    def _get_all_pages(self, endpoint: str, params: dict) -> list[dict]:
        all_results = []
        page = 1

        while True:
            params["page"] = page
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            all_results.extend(data.get("results", []))

            # Check if there are more pages
            total = data.get("total", 0)
            if len(all_results) >= total or len(data.get("results", [])) == 0:
                break

            page += 1

        return all_results

    def _format_datetime_for_api(self, dt: datetime) -> str:
        iso_str = dt.isoformat()
        # Replace +00:00 or -00:00 with Z (UTC indicator)
        if iso_str.endswith("+00:00") or iso_str.endswith("-00:00"):
            return iso_str[:-6] + "Z"
        elif "+" in iso_str or (len(iso_str) >= 6 and iso_str[-6] in "+-"):
            # Has timezone offset, keep as is
            return iso_str
        else:
            # No timezone, assume UTC and add Z
            return iso_str + "Z"

    def _chunk_time_range(
        self,
        time_from: datetime,
        time_to: datetime,
    ) -> list[tuple[datetime, datetime]]:
        chunks = []
        current_to = time_to

        while current_to > time_from:
            current_from = max(time_from, current_to - timedelta(days=7))
            chunks.append((current_from, current_to))
            # Move back, with 1 second overlap to avoid gaps
            current_to = current_from - timedelta(seconds=1)

        return chunks

    def get_operations(
        self,
        time_from: datetime,
        time_to: datetime,
    ) -> list[dict]:
        all_results = []

        chunks = self._chunk_time_range(time_from, time_to)
        print(
            f"   Splitting time range into {len(chunks)} chunks of 7 days each...",
        )

        for i, (chunk_from, chunk_to) in enumerate(chunks, 1):
            print(
                f"   Fetching chunk {i}/{len(chunks)}: "
                f"{chunk_from.date()} to {chunk_to.date()}",
            )
            chunk_results = self._get_all_pages(
                "/operations",
                {
                    "time_from": self._format_datetime_for_api(chunk_from),
                    "time_to": self._format_datetime_for_api(chunk_to),
                    "integration": INTEGRATION_TYPE,
                },
            )
            all_results.extend(chunk_results)

        return all_results

    def get_task_runs(
        self,
        time_from: datetime,
        time_to: datetime,
    ) -> list[dict]:
        all_results = []

        chunks = self._chunk_time_range(time_from, time_to)
        print(
            f"   Splitting time range into {len(chunks)} chunks of 7 days each...",
        )

        for i, (chunk_from, chunk_to) in enumerate(chunks, 1):
            print(
                f"   Fetching chunk {i}/{len(chunks)}: "
                f"{chunk_from.date()} to {chunk_to.date()}",
            )
            chunk_results = self._get_all_pages(
                "/task_runs",
                {
                    "time_from": self._format_datetime_for_api(chunk_from),
                    "time_to": self._format_datetime_for_api(chunk_to),
                    "integration": INTEGRATION_TYPE,
                },
            )
            all_results.extend(chunk_results)

        return all_results


def calculate_time_range(
    days: int = DEFAULT_ANALYSIS_DAYS,
) -> tuple[datetime, datetime]:
    time_to = datetime.now(timezone.utc)
    time_from = time_to - timedelta(days=days)
    return time_from, time_to


def plot_total_operation_duration_by_state_orchestration(
    operations: list[dict],
    task_runs: list[dict],
):
    if not operations or not task_runs:
        print("No data available for total operation duration analysis")
        return

    # Convert to DataFrames
    ops_df = pd.DataFrame(operations)
    task_runs_df = pd.DataFrame(task_runs)

    if ops_df.empty or task_runs_df.empty:
        print("No data available for total operation duration analysis")
        return

    # Parse timestamps
    if "insertedAt" in ops_df.columns:
        ops_df["insertedAt"] = pd.to_datetime(ops_df["insertedAt"], errors="coerce")
    if "createdAt" in task_runs_df.columns:
        task_runs_df["createdAt"] = pd.to_datetime(
            task_runs_df["createdAt"],
            errors="coerce",
        )

    # Extract use_state_orchestration from task_parameters
    if "taskParameters" in task_runs_df.columns:
        task_runs_df["use_state_orchestration"] = task_runs_df["taskParameters"].apply(
            lambda x: x.get("use_state_orchestration", False)
            if isinstance(x, dict)
            else False,
        )
    else:
        task_runs_df["use_state_orchestration"] = False

    # Get task_run_id field name (could be taskRunId from API or task_run_id from DB)
    task_run_id_col = None
    for col in ["taskRunId", "task_run_id", "id"]:
        if col in task_runs_df.columns:
            task_run_id_col = col
            break

    if task_run_id_col is None:
        print("Could not find task_run_id field in task runs data")
        return

    # Get task name field name (could be taskName or task_name)
    task_name_col = None
    for col in ["taskName", "task_name"]:
        if col in task_runs_df.columns:
            task_name_col = col
            break

    if task_name_col is None:
        print("Could not find task_name field in task runs data")
        return

    # Get operation task_run_id field name
    op_task_run_id_col = None
    for col in ["taskRunId", "task_run_id"]:
        if col in ops_df.columns:
            op_task_run_id_col = col
            break

    if op_task_run_id_col is None:
        print("Could not find task_run_id field in operations data")
        return

    # Get operation duration field name (could be operationDuration or operation_duration)
    op_duration_col = None
    for col in ["operationDuration", "operation_duration"]:
        if col in ops_df.columns:
            op_duration_col = col
            break

    if op_duration_col is None:
        print("Could not find operation_duration field in operations data")
        return

    # Filter operations to only those with valid task_run_id and duration
    ops_df = ops_df[
        ops_df[op_task_run_id_col].notna()
        & ops_df[op_duration_col].notna()
        & (ops_df[op_duration_col] > 0)
    ].copy()

    # Convert task_run_id to string for consistent merging
    ops_df[op_task_run_id_col] = ops_df[op_task_run_id_col].astype(str)
    task_runs_df[task_run_id_col] = task_runs_df[task_run_id_col].astype(str)

    # Calculate total duration per task run
    task_run_totals = (
        ops_df.groupby(op_task_run_id_col)[op_duration_col].sum().reset_index()
    )
    task_run_totals.columns = [task_run_id_col, "total_duration_seconds"]

    # Merge with task runs to get task name, date, and state orchestration status
    merged_df = task_runs_df.merge(
        task_run_totals,
        on=task_run_id_col,
        how="inner",
    )

    # Determine which tasks have ever had state orchestration enabled
    tasks_with_state_orch = set(
        task_runs_df[task_runs_df["use_state_orchestration"]][task_name_col].unique(),
    )

    # Filter to only tasks that have used state orchestration
    tasks_with_state_orch_list = list(tasks_with_state_orch)
    if not tasks_with_state_orch_list:
        print("No tasks found that have used state orchestration")
        return

    merged_df_filtered = merged_df[
        merged_df[task_name_col].isin(tasks_with_state_orch_list)
    ].copy()

    # Calculate days before/after first state orchestration use for each task
    task_stats = []
    for task_name in tasks_with_state_orch_list:
        task_data = merged_df_filtered[
            merged_df_filtered[task_name_col] == task_name
        ].sort_values(
            "createdAt",
        )

        # Find first use of state orchestration
        first_state_orch = task_data[task_data["use_state_orchestration"]]
        if first_state_orch.empty:
            continue

        first_state_orch_date = first_state_orch.iloc[0]["createdAt"]

        # Calculate days before/after first use
        task_data["days_from_first_use"] = (
            task_data["createdAt"] - first_state_orch_date
        ).dt.total_seconds() / (24 * 3600)

        # Split into before and after
        before = task_data[task_data["days_from_first_use"] < 0]
        after = task_data[task_data["days_from_first_use"] >= 0]

        # Calculate averages
        avg_before = (
            before["total_duration_seconds"].mean() if not before.empty else None
        )
        avg_after = after["total_duration_seconds"].mean() if not after.empty else None

        # Calculate percentage change
        if avg_before is not None and avg_after is not None and avg_before > 0:
            pct_change = ((avg_after - avg_before) / avg_before) * 100
        else:
            pct_change = None

        task_stats.append(
            {
                "task_name": task_name,
                "avg_before": avg_before,
                "avg_after": avg_after,
                "pct_change": pct_change,
                "first_use_date": first_state_orch_date,
                "task_data": task_data,
            },
        )

    if not task_stats:
        print("No valid task data found")
        return

    # Create the plot
    fig, (ax, ax_table) = plt.subplots(
        2,
        1,
        figsize=(FIGURE_WIDTH, FIGURE_HEIGHT),
        gridspec_kw={"height_ratios": [PLOT_HEIGHT_RATIO, TABLE_HEIGHT_RATIO]},
    )

    # Plot one line for each task name
    for idx, stat in enumerate(task_stats):
        task_name = stat["task_name"]
        task_data = stat["task_data"]
        color = COLOR_PALETTE[idx % len(COLOR_PALETTE)]

        # Plot the line for this task
        ax.plot(
            task_data["days_from_first_use"],
            task_data["total_duration_seconds"],
            marker="o",
            linewidth=LINE_WIDTH,
            markersize=MARKER_SIZE,
            label=task_name,
            color=color,
            alpha=LINE_ALPHA,
        )

        # Highlight the first use (at 0 days)
        first_use_data = task_data[task_data["days_from_first_use"] >= 0]
        first_use_point = first_use_data.iloc[0] if len(first_use_data) > 0 else None
        if first_use_point is not None:
            ax.scatter(
                first_use_point["days_from_first_use"],
                first_use_point["total_duration_seconds"],
                marker="*",
                s=FIRST_USE_MARKER_SIZE,
                color=FIRST_USE_MARKER_COLOR,
                edgecolors=FIRST_USE_MARKER_EDGE_COLOR,
                linewidths=FIRST_USE_MARKER_EDGE_WIDTH,
                zorder=5,
            )

    ax.set_title(
        (
            "Total Operation Duration per Task Run: "
            "Days Before/After First State Orchestration Use (dbt Core)"
        ),
        fontsize=TITLE_FONTSIZE,
        fontweight="bold",
    )
    ax.set_xlabel(
        "Days from First State Orchestration Use (0 = first use)",
        fontsize=AXIS_LABEL_FONTSIZE,
    )
    ax.set_ylabel("Total Duration (seconds)", fontsize=AXIS_LABEL_FONTSIZE)
    ax.grid(True, alpha=GRID_ALPHA, linestyle="--")

    # Get existing legend handles and labels
    handles, labels = ax.get_legend_handles_labels()

    # Add custom legend entry for gold star
    gold_star_legend = Line2D(
        [0],
        [0],
        marker="*",
        color="w",
        markerfacecolor=FIRST_USE_MARKER_COLOR,
        markersize=12,
        label="First use of State Orchestration",
        markeredgecolor=FIRST_USE_MARKER_EDGE_COLOR,
        markeredgewidth=FIRST_USE_MARKER_EDGE_WIDTH,
    )
    handles.append(gold_star_legend)
    labels.append("First use of State Orchestration")

    ax.legend(handles=handles, labels=labels, loc="best", fontsize=LEGEND_FONTSIZE)

    # Create table with percentage changes
    table_data = []
    for stat in task_stats:
        pct_change = stat["pct_change"]
        if pct_change is not None:
            change_str = f"{pct_change:+.1f}%"
            color_indicator = "↓" if pct_change < 0 else "↑"
        else:
            change_str = "N/A"
            color_indicator = ""
        table_data.append(
            [
                stat["task_name"],
                f"{stat['avg_before']:.1f}"
                if stat["avg_before"] is not None
                else "N/A",
                f"{stat['avg_after']:.1f}" if stat["avg_after"] is not None else "N/A",
                f"{change_str} {color_indicator}",
            ],
        )

    table = ax_table.table(
        cellText=table_data,
        colLabels=["Task Name", "Avg Before (s)", "Avg After (s)", "Change"],
        cellLoc="left",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(TABLE_FONTSIZE)
    table.scale(1, TABLE_SCALE_Y)
    ax_table.axis("off")

    ax.tick_params(axis="x", rotation=0)

    plt.tight_layout()
    plt.show()


def main():
    if not ORCHESTRA_API_KEY:
        raise ValueError("ORCHESTRA_API_KEY environment variable must be set")

    client = OrchestraAPIClient(ORCHESTRA_API_KEY)
    time_from, time_to = calculate_time_range(days=DEFAULT_ANALYSIS_DAYS)
    all_operations = client.get_operations(time_from=time_from, time_to=time_to)
    print(f"   Found {len(all_operations)} total operations")

    task_runs = client.get_task_runs(time_from=time_from, time_to=time_to)
    print(f"   Found {len(task_runs)} task runs")

    plot_total_operation_duration_by_state_orchestration(
        operations=all_operations,
        task_runs=task_runs,
    )

    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()
