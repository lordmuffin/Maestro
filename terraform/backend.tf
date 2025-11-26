# Backend configuration for Terraform state management
#
# Google Cloud Storage backend for multi-environment state management
#
# State prefix is configured via CLI at init time:
# - Staging:    terraform init -backend-config="prefix=terraform/state/staging"
# - Production: terraform init -backend-config="prefix=terraform/state/production"
#
# This allows separate state files per environment:
#   gs://project-maestro-tfstate/terraform/state/staging/default.tfstate
#   gs://project-maestro-tfstate/terraform/state/production/default.tfstate

terraform {
  backend "gcs" {
    # Bucket is configured via CLI: -backend-config="bucket=project-maestro-tfstate"
    # Prefix is configured per environment (see above)
  }
}

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
