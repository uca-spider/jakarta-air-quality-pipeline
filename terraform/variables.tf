variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Region for the bucket and BigQuery datasets"
  type        = string
  default     = "asia-southeast2"
}

variable "raw_bucket_name" {
  description = "Globally unique name for the raw data bucket"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository allowed to authenticate, as owner/name"
  type        = string
  default     = "uca-spider/jakarta-air-quality-pipeline"
}
