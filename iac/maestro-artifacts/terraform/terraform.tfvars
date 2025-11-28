# V2V2B Interrogator - Terraform Variables
# This file uses environment variables from GitHub Actions
# Local values can be overridden for local development

# GCP Project Configuration
gcp_project = "gen-lang-client-0805519538"
region      = "us-central1"

# GitHub Integration
# These will be populated from GitHub secrets in CI/CD
github_token = "" # Set via TF_VAR_github_token in GitHub Actions
repo_name    = "lordmuffin/Maestro"

# Google Drive Integration (Optional)
# Add your folder IDs here or in GitHub environment variables
google_drive_folder_id   = ""
obsidian_drive_folder_id = ""
kanban_folder_id         = ""
beyond_repo_name         = "lordmuffin/beyond"
drive_poll_interval      = 300

# Function Configuration
function_name = "v2v2b-interrogator"
function_url  = "" # Will be populated after first deployment

# Resource Configuration
memory             = "512Mi"
timeout_seconds    = 540
max_instance_count = 10
min_instance_count = 0

# Firestore Rules
deploy_firestore_rules = true

# Resource Labels
labels = {
  application = "v2v2b-interrogator"
  managed-by  = "terraform"
  environment = "production"
}
