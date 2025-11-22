# Backend configuration for Terraform state management
#
# Uncomment and configure one of the following backends:

# Option 1: Google Cloud Storage (Recommended for GCP deployments)
# terraform {
#   backend "gcs" {
#     bucket = "your-terraform-state-bucket"
#     prefix = "v2v2b-interrogator/state"
#   }
# }

# Option 2: Terraform Cloud (Recommended for team collaboration)
# terraform {
#   cloud {
#     organization = "your-organization"
#     workspaces {
#       name = "v2v2b-interrogator"
#     }
#   }
# }

# Option 3: Local backend (Default - not recommended for production)
# State will be stored locally in terraform.tfstate
# No configuration needed - this is the default behavior

# To initialize GCS backend:
# 1. Create a GCS bucket for state storage:
#    gsutil mb gs://your-terraform-state-bucket
#
# 2. Enable versioning (recommended):
#    gsutil versioning set on gs://your-terraform-state-bucket
#
# 3. Uncomment the "gcs" backend configuration above
#
# 4. Run: terraform init -migrate-state
