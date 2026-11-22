"""BigQuery client factory.

Uses Application Default Credentials (keyless / Workload Identity). No key
files are read or created.
"""

from google.cloud import bigquery


def make_bigquery_client(project: str) -> bigquery.Client:
    """Return a BigQuery client for the given project (ADC auth)."""
    return bigquery.Client(project=project)
