"""dlt sources for the platform-lineage pipeline.

One module per platform. Each exposes a `<platform>_source()` returning a dlt
source, and every resource it yields is prefixed with the platform name so the
raw dataset stays readable (`lightdash_charts`, `fivetran_connectors`, ...).
"""
