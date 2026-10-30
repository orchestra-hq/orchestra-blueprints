{#
  Same as snowplow_unified's default stitching post-hook, except rows that
  already hold the mapped user_id are skipped. The package's UPDATE matches
  every historical row of every mapped user on each run, so Snowflake
  rewrites those micro-partitions even though nothing changes; skipping
  them leaves the output identical. Picked up through the snowplow_unified
  dispatch entry in dbt_project.yml.
  TEST ONLY: off unless var sim_stitch_fix is true.
#}
{% macro snowflake__stitch_user_identifiers(enabled, relation=this, user_mapping_relation='snowplow_unified_user_mapping') %}
  {% if not var('sim_stitch_fix', false) %}
    {{ return(snowplow_unified.default__stitch_user_identifiers(enabled, relation, user_mapping_relation)) }}
  {% endif %}
  {% if enabled | as_bool() %}
    update {{ relation }} as s
    set stitched_user_id = um.user_id
    from {{ ref(user_mapping_relation) }} as um
    where s.user_identifier = um.user_identifier
      and s.stitched_user_id is distinct from um.user_id;
  {% endif %}
{%- endmacro %}
