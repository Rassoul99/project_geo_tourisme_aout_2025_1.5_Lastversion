terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.74.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required services
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com"
  ])

  project = var.project_id
  service = each.key

  disable_on_destroy = false
}

# Create Artifact Registry repository
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "smart-travel-planner"
  description   = "Repository for Smart Travel Planner Docker images"
  format        = "DOCKER"
}

# Create Cloud SQL instance
resource "google_sql_database_instance" "postgres" {
  name             = "smart-travel-postgres"
  database_version = "POSTGRES_14"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "REGIONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }

    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }
  }

  deletion_protection = false
}

# Create Cloud Storage bucket for backups
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-backups"
  location      = var.region
  force_destroy = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Create Cloud Scheduler job for backups
resource "google_cloud_scheduler_job" "backup_job" {
  name        = "daily-backup-job"
  description = "Daily backup of application data"
  schedule    = "0 3 * * 1" # Every Monday at 3 AM

  http_target {
    http_method = "GET"
    uri          = "https://${var.region}-${var.project_id}.cloudfunctions.net/backup-function"

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

# Create service account for Cloud Scheduler
resource "google_service_account" "scheduler" {
  account_id   = "scheduler-sa"
  display_name = "Cloud Scheduler Service Account"
}

# Create Cloud Function for backups
resource "google_cloudfunctions_function" "backup_function" {
  name        = "backup-function"
  description = "Function to handle daily backups"
  runtime     = "python39"

  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.backups.name
  source_archive_object = "backup-function.zip"
  trigger_http          = true
  entry_point           = "backup_handler"
  timeout               = 60

  environment_variables = {
    BUCKET_NAME = google_storage_bucket.backups.name
  }
}

# Create Secret Manager secrets
resource "google_secret_manager_secret" "api_keys" {
  for_each = toset(["GOOGLE_PLACES_KEY", "OPENWEATHERMAP_KEY", "MISTRAL_API_KEY"])

  secret_id = each.key

  replication {
    automatic = true
  }
}

# Create Monitoring dashboard
resource "google_monitoring_dashboard" "app_dashboard" {
  dashboard_json = file("${path.module}/monitoring/dashboards/app_dashboard.json")
}
