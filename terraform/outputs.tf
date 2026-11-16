# Copy these into GitHub: Settings > Secrets and variables > Actions > Variables.
# They are identifiers, not secrets. No JSON key is created or stored anywhere.

output "GCP_WIF_PROVIDER" {
  value = google_iam_workload_identity_pool_provider.github.name
}

output "GCP_INGEST_SA" {
  value = google_service_account.ingest.email
}

output "RAW_BUCKET" {
  value = google_storage_bucket.raw.name
}
