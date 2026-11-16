# Service account used by the scheduled ingestion workflows
resource "google_service_account" "ingest" {
  account_id   = "aq-ingest"
  display_name = "Air quality ingestion (GitHub Actions)"

  depends_on = [google_project_service.apis]
}

# Least privilege: scoped to one bucket and two datasets, plus the ability to run jobs
resource "google_storage_bucket_iam_member" "ingest_bucket" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectAdmin" # needed to overwrite objects; scoped to this bucket only
  member = "serviceAccount:${google_service_account.ingest.email}"
}

resource "google_bigquery_dataset_iam_member" "ingest_raw" {
  dataset_id = google_bigquery_dataset.aq["aq_raw"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingest.email}"
}

resource "google_bigquery_dataset_iam_member" "ingest_staging" {
  dataset_id = google_bigquery_dataset.aq["aq_staging"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingest.email}"
}

resource "google_project_iam_member" "ingest_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingest.email}"
}

# Keyless authentication from GitHub Actions (Workload Identity Federation)
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Only this repository may use the pool
  attribute_condition = "assertion.repository == \"${var.github_repo}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_can_impersonate" {
  service_account_id = google_service_account.ingest.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
