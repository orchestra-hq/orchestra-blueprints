# sao_v2_runner

Not a dbt project. An Orchestra dbt Core task points `project_dir` here so it
can run `orc dbt build --project-dir ../bigquery_sao_v2_edge` from outside the
project. `sao_v2_mixed_runner` does the same with dbt 1.x and v2 installed side
by side.
