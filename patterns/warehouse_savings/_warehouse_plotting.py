"""Plotting helpers for warehouse savings analysis."""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

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

COLOR_PALETTE = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]
FIRST_USE_MARKER_COLOR = "gold"
FIRST_USE_MARKER_EDGE_COLOR = "black"
FIRST_USE_MARKER_EDGE_WIDTH = 1.5


def plot_total_operation_duration_by_state_orchestration(
    operations: list[dict],
    task_runs: list[dict],
) -> None:
    if not operations or not task_runs:
        print("No data available for total operation duration analysis")
        return

    ops_df = pd.DataFrame(operations)
    task_runs_df = pd.DataFrame(task_runs)

    if ops_df.empty or task_runs_df.empty:
        print("No data available for total operation duration analysis")
        return

    if "insertedAt" in ops_df.columns:
        ops_df["insertedAt"] = pd.to_datetime(ops_df["insertedAt"], errors="coerce")
    if "createdAt" in task_runs_df.columns:
        task_runs_df["createdAt"] = pd.to_datetime(
            task_runs_df["createdAt"], errors="coerce"
        )

    if "taskParameters" in task_runs_df.columns:
        task_runs_df["use_state_orchestration"] = task_runs_df["taskParameters"].apply(
            lambda x: (
                x.get("use_state_orchestration", False)
                if isinstance(x, dict)
                else False
            ),
        )
    else:
        task_runs_df["use_state_orchestration"] = False

    task_run_id_col = None
    for col in ["taskRunId", "task_run_id", "id"]:
        if col in task_runs_df.columns:
            task_run_id_col = col
            break
    if task_run_id_col is None:
        print("Could not find task_run_id field in task runs data")
        return

    task_name_col = None
    for col in ["taskName", "task_name"]:
        if col in task_runs_df.columns:
            task_name_col = col
            break
    if task_name_col is None:
        print("Could not find task_name field in task runs data")
        return

    op_task_run_id_col = None
    for col in ["taskRunId", "task_run_id"]:
        if col in ops_df.columns:
            op_task_run_id_col = col
            break
    if op_task_run_id_col is None:
        print("Could not find task_run_id field in operations data")
        return

    op_duration_col = None
    for col in ["operationDuration", "operation_duration"]:
        if col in ops_df.columns:
            op_duration_col = col
            break
    if op_duration_col is None:
        print("Could not find operation_duration field in operations data")
        return

    ops_df = ops_df[
        ops_df[op_task_run_id_col].notna()
        & ops_df[op_duration_col].notna()
        & (ops_df[op_duration_col] > 0)
    ].copy()

    ops_df[op_task_run_id_col] = ops_df[op_task_run_id_col].astype(str)
    task_runs_df[task_run_id_col] = task_runs_df[task_run_id_col].astype(str)

    task_run_totals = (
        ops_df.groupby(op_task_run_id_col)[op_duration_col].sum().reset_index()
    )
    task_run_totals.columns = [task_run_id_col, "total_duration_seconds"]

    merged_df = task_runs_df.merge(task_run_totals, on=task_run_id_col, how="inner")

    tasks_with_state_orch = set(
        task_runs_df[task_runs_df["use_state_orchestration"]][task_name_col].unique(),
    )
    tasks_with_state_orch_list = list(tasks_with_state_orch)
    if not tasks_with_state_orch_list:
        print("No tasks found that have used state orchestration")
        return

    merged_df_filtered = merged_df[
        merged_df[task_name_col].isin(tasks_with_state_orch_list)
    ].copy()

    task_stats = []
    for task_name in tasks_with_state_orch_list:
        task_data = merged_df_filtered[
            merged_df_filtered[task_name_col] == task_name
        ].sort_values("createdAt")

        first_state_orch = task_data[task_data["use_state_orchestration"]]
        if first_state_orch.empty:
            continue

        first_state_orch_date = first_state_orch.iloc[0]["createdAt"]
        task_data["days_from_first_use"] = (
            task_data["createdAt"] - first_state_orch_date
        ).dt.total_seconds() / (24 * 3600)

        before = task_data[task_data["days_from_first_use"] < 0]
        after = task_data[task_data["days_from_first_use"] >= 0]

        avg_before = (
            before["total_duration_seconds"].mean() if not before.empty else None
        )
        avg_after = after["total_duration_seconds"].mean() if not after.empty else None

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
                "task_data": task_data,
            },
        )

    if not task_stats:
        print("No valid task data found")
        return

    _, (ax, ax_table) = plt.subplots(
        2,
        1,
        figsize=(FIGURE_WIDTH, FIGURE_HEIGHT),
        gridspec_kw={"height_ratios": [PLOT_HEIGHT_RATIO, TABLE_HEIGHT_RATIO]},
    )

    for idx, stat in enumerate(task_stats):
        task_data = stat["task_data"]
        color = COLOR_PALETTE[idx % len(COLOR_PALETTE)]

        ax.plot(
            task_data["days_from_first_use"],
            task_data["total_duration_seconds"],
            marker="o",
            linewidth=LINE_WIDTH,
            markersize=MARKER_SIZE,
            label=stat["task_name"],
            color=color,
            alpha=LINE_ALPHA,
        )

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
        "Total Operation Duration per Task Run: Days Before/After First State Orchestration Use (dbt Core)",
        fontsize=TITLE_FONTSIZE,
        fontweight="bold",
    )
    ax.set_xlabel(
        "Days from First State Orchestration Use (0 = first use)",
        fontsize=AXIS_LABEL_FONTSIZE,
    )
    ax.set_ylabel("Total Duration (seconds)", fontsize=AXIS_LABEL_FONTSIZE)
    ax.grid(True, alpha=GRID_ALPHA, linestyle="--")

    handles, labels = ax.get_legend_handles_labels()
    handles.append(
        Line2D(
            [0],
            [0],
            marker="*",
            color="w",
            markerfacecolor=FIRST_USE_MARKER_COLOR,
            markersize=12,
            label="First use of State Orchestration",
            markeredgecolor=FIRST_USE_MARKER_EDGE_COLOR,
            markeredgewidth=FIRST_USE_MARKER_EDGE_WIDTH,
        ),
    )
    labels.append("First use of State Orchestration")
    ax.legend(handles=handles, labels=labels, loc="best", fontsize=LEGEND_FONTSIZE)

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
