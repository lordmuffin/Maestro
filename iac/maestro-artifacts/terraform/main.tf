# Prerequisites:
# IMPORTANT: The following must be completed before running Terraform:
#
# 1. BILLING ACCOUNT: Enable billing for the GCP project
#    - Go to: https://console.cloud.google.com/billing/linkedaccount?project=<PROJECT_ID>
#    - Associate a valid billing account with the project
#    - Required for Cloud Build, Cloud Run, Cloud Storage, and other paid services
#
# 2. ENABLE BOOTSTRAP APIs: Manually enable these APIs first
#    - Service Usage API (serviceusage.googleapis.com)
#    - Identity and Access Management (IAM) API (iam.googleapis.com)
#    Via gcloud: gcloud services enable serviceusage.googleapis.com iam.googleapis.com --project=<PROJECT_ID>
#    Via Console: https://console.developers.google.com/apis/api/serviceusage.googleapis.com/overview
#
# 3. SERVICE ACCOUNT PERMISSIONS: Grant required roles to the deployment service account
#    Required roles for the service account used by GitHub Actions:
#    - roles/editor (Project Editor) OR roles/owner (Project Owner)
#    - roles/serviceusage.serviceUsageAdmin (Service Usage Admin)
#    - roles/iam.serviceAccountAdmin (Service Account Admin) 
#    - roles/resourcemanager.projectIamAdmin (Project IAM Admin)
#
#    Grant roles via: 
#    gcloud projects add-iam-policy-binding <PROJECT_ID> --member='serviceAccount:<SA_EMAIL>' --role='<ROLE>'

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


resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "drive" {
  service            = "drive.googleapis.com"
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

locals {
  maestro_custom_config_json = (var.custom_mcp_endpoint_url != null && var.custom_mcp_endpoint_url != "") ? jsonencode({
    // 'my_custom_server' is the internal tool name the LLM will see
    my_custom_server = {
      url  = var.custom_mcp_endpoint_url
      type = "http" // Assume HTTP/SSE connection for remote servers
    }
  }) : "{}"
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

  # Include prompt files
  source {
    content  = file("${path.module}/../prompts/telegram_chat_prompt.md")
    filename = "prompts/telegram_chat_prompt.md"
  }

  source {
    content  = file("${path.module}/../prompts/multimodal_analysis_prompt.md")
    filename = "prompts/multimodal_analysis_prompt.md"
  }

  source {
    content  = file("${path.module}/../prompts/transcript_analysis_prompt.md")
    filename = "prompts/transcript_analysis_prompt.md"
  }

  source {
    content  = file("${path.module}/../prompts/interrogation_questions_prompt.md")
    filename = "prompts/interrogation_questions_prompt.md"
  }

  source {
    content  = file("${path.module}/../prompts/interviewer_prompt.md")
    filename = "prompts/interviewer_prompt.md"
  }

  source {
    content  = file("${path.module}/../prompts/file_validation_prompt.md")
    filename = "prompts/file_validation_prompt.md"
  }

  # Include repository configuration file
  source {
    content  = file("${path.module}/${var.repos_config_file}")
    filename = "repos.json"
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
  description = "V2V2B Interrogator - Telegram Bot for Technical Content Extraction"

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

    environment_variables = merge(
      {
        GCP_PROJECT              = var.gcp_project
        TELEGRAM_BOT_TOKEN       = var.telegram_bot_token
        GOOGLE_DRIVE_FOLDER_ID   = var.google_drive_folder_id
        OBSIDIAN_DRIVE_FOLDER_ID = var.obsidian_drive_folder_id
        KANBAN_FOLDER_ID         = var.kanban_folder_id
        DRIVE_POLL_INTERVAL      = tostring(var.drive_poll_interval)
        # Note: FUNCTION_URL is set via output after first deployment
        FUNCTION_URL              = var.function_url != "" ? var.function_url : "https://${var.region}-${var.gcp_project}.cloudfunctions.net/${var.function_name}"
        MAESTRO_CUSTOM_MCP_CONFIG = local.maestro_custom_config_json
      },
      # Add per-repository GitHub tokens
      {
        for label, token in var.github_tokens :
        "GITHUB_TOKEN_${upper(label)}" => token
      }
    )

    dynamic "secret_environment_variables" {
      for_each = var.custom_mcp_auth_secret_name != null ? [1] : []
      content {
        key        = "CUSTOM_MCP_AUTH_KEY"
        project_id = var.gcp_project
        secret     = var.custom_mcp_auth_secret_name
        version    = "latest"
      }
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

# Note: For Telegram webhook, the function only needs to be publicly accessible
# via google_cloud_run_service_iam_member.public_access

resource "google_project_iam_member" "logging_writer" {
  project = var.gcp_project
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

# Google Drive Access:
# Note: Drive access is granted by sharing specific Drive folders with the service account.
# There is no project-level IAM role for Drive access. Instead:
# 1. Get the service account email: terraform output service_account_email
# 2. Share your Drive folders with this email address:
#    - Transcript folder: Grant "Viewer" access
#    - Obsidian folder: Grant "Editor" access
# The Drive API service must be enabled (handled by google_project_service.drive)

# Allow unauthenticated access to the function (for Telegram webhook)
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
      name    = "firestore.rules"
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
