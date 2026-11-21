{#
    Macro to override dbt's default schema naming behavior.
    By default, dbt prefixes custom schema with the target dataset (e.g. aq_staging_aq_staging).
    This macro ensures the exact custom schema name is used directly (e.g. aq_staging, aq_marts).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
