# Prerequisites:
# The following APIs must be manually enabled in the GCP project before running Terraform:
# 1. Service Usage API (serviceusage.googleapis.com)
# 2. Identity and Access Management (IAM) API (iam.googleapis.com)
# 
# These can be enabled via:
# gcloud services enable serviceusage.googleapis.com iam.googleapis.com --project=<PROJECT_ID>
# 
# Or through the GCP Console at:
# https://console.developers.google.com/apis/api/serviceusage.googleapis.com/overview
# https://console.developers.google.com/apis/api/iam.googleapis.com/overview

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.region
}

# Enable required APIs
# Note: Service Usage API and IAM API must be manually enabled in the GCP Console first
# or through gcloud CLI before running Terraform

resource "google_project_service" "cloud_functions" {
  service            = "cloudfunctions.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_build" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firestore" {
  service            = "firestore.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "aiplatform" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "chat" {
  service            = "chat.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

# Create Firestore Database (only if it doesn't exist)
resource "google_firestore_database" "database" {
  project     = var.gcp_project
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.firestore]

  # Prevent destruction of existing database
  lifecycle {
    prevent_destroy = false
    ignore_changes  = [name]
  }
}

# Create a GCS bucket for function source code
resource "google_storage_bucket" "function_bucket" {
  name          = "${var.gcp_project}-v2v2b-function-source"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  depends_on = [google_project_service.cloud_functions]
}

# Create ZIP archive of function source code
data "archive_file" "function_source" {
  type        = "zip"
  output_path = "${path.module}/.terraform/function-source.zip"

  source {
    content  = file("${path.module}/main.py")
    filename = "main.py"
  }

  source {
    content  = file("${path.module}/requirements.txt")
    filename = "requirements.txt"
  }
}

# Upload function source to GCS
resource "google_storage_bucket_object" "function_source" {
  name   = "function-source-${data.archive_file.function_source.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.function_source.output_path
}

# Create the Cloud Function (Gen 2)
resource "google_cloudfunctions2_function" "v2v2b_interrogator" {
  name        = var.function_name
  location    = var.region
  description = "V2V2B Interrogator - Google Chat Bot for Technical Content Extraction"

  build_config {
    runtime     = "python311"
    entry_point = "entry_point"

    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    max_instance_count = var.max_instance_count
    min_instance_count = var.min_instance_count
    available_memory   = var.memory
    timeout_seconds    = var.timeout_seconds

    environment_variables = {
      GCP_PROJECT  = var.gcp_project
      GITHUB_TOKEN = var.github_token
      REPO_NAME    = var.repo_name
      # Note: FUNCTION_URL is set via output after first deployment
      FUNCTION_URL = var.function_url != "" ? var.function_url : "https://${var.region}-${var.gcp_project}.cloudfunctions.net/${var.function_name}"
    }

    ingress_settings               = "ALLOW_ALL"
    all_traffic_on_latest_revision = true

    service_account_email = google_service_account.function_sa.email
  }

  depends_on = [
    google_project_service.cloud_functions,
    google_project_service.cloud_build,
    google_project_service.cloud_run,
    google_firestore_database.database
  ]
}

# Create service account for the function
resource "google_service_account" "function_sa" {
  account_id   = "${var.function_name}-sa"
  display_name = "Service Account for V2V2B Interrogator Function"
}

# Grant necessary IAM roles to the service account
resource "google_project_iam_member" "firestore_user" {
  project = var.gcp_project
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_project_iam_member" "aiplatform_user" {
  project = var.gcp_project
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_project_iam_member" "chat_bot" {
  project = var.gcp_project
  role    = "roles/chat.bot"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_project_iam_member" "logging_writer" {
  project = var.gcp_project
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

# Allow unauthenticated access to the function (for Google Chat webhook)
resource "google_cloud_run_service_iam_member" "public_access" {
  project  = google_cloudfunctions2_function.v2v2b_interrogator.project
  location = google_cloudfunctions2_function.v2v2b_interrogator.location
  service  = google_cloudfunctions2_function.v2v2b_interrogator.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Optional: Deploy Firestore security rules
resource "google_firebaserules_ruleset" "firestore" {
  count = var.deploy_firestore_rules ? 1 : 0

  source {
    files {
      name = "firestore.rules"
      content = file("${path.module}/firestore.rules")
    }
  }

  depends_on = [google_firestore_database.database]
}

resource "google_firebaserules_release" "firestore" {
  count = var.deploy_firestore_rules ? 1 : 0

  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.firestore[0].name

  depends_on = [google_firebaserules_ruleset.firestore]

  lifecycle {
    replace_triggered_by = [
      google_firebaserules_ruleset.firestore
    ]
  }
}
