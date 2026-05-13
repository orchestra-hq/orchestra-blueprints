import os

import matplotlib.pyplot as plt

from _warehouse_api import (
    DEFAULT_ANALYSIS_DAYS,
    OrchestraAPIClient,
    calculate_time_range,
)
from _warehouse_plotting import (
    FIGURE_HEIGHT,
    FIGURE_WIDTH,
    plot_total_operation_duration_by_state_orchestration,
)

ORCHESTRA_API_KEY = os.getenv("ORCHESTRA_API_KEY")

plt.rcParams["figure.figsize"] = (FIGURE_WIDTH, FIGURE_HEIGHT)


def main() -> None:
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
