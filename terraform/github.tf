# GitHub Repository resource
resource "github_repository" "repo" {
  name        = "jakarta-air-quality-pipeline"
  description = "Jakarta ISPU Air Quality automated ELT data pipeline with GCP, BigQuery, dbt, and GitHub Actions."
  visibility  = "public"

  has_issues   = true
  has_projects = false
  has_wiki     = false
}

# Automatically provision GitHub Actions Variables directly into the repository
resource "github_actions_variable" "wif_provider" {
  repository    = github_repository.repo.name
  variable_name = "GCP_WIF_PROVIDER"
  value         = google_iam_workload_identity_pool_provider.github.name
}

resource "github_actions_variable" "ingest_sa" {
  repository    = github_repository.repo.name
  variable_name = "GCP_INGEST_SA"
  value         = google_service_account.ingest.email
}

resource "github_actions_variable" "raw_bucket" {
  repository    = github_repository.repo.name
  variable_name = "RAW_BUCKET"
  value         = google_storage_bucket.raw.name
}
