#!/bin/bash
# Import existing GCP resources into Terraform state for production environment

set -e

PROJECT_ID="project-maestro-gcp"
ENVIRONMENT="production"

echo "🔄 Importing existing GCP resources into Terraform state for $ENVIRONMENT..."

# Navigate to terraform directory
cd "$(dirname "$0")"

# Select workspace
echo "Selecting workspace: $ENVIRONMENT"
terraform workspace select $ENVIRONMENT || terraform workspace new $ENVIRONMENT

# Import service account
echo "Importing service account..."
terraform import google_service_account.function_sa "projects/$PROJECT_ID/serviceAccounts/v2v2b-interrogator-sa@$PROJECT_ID.iam.gserviceaccount.com" || echo "⚠️ Service account import failed (may already be in state)"

echo "✅ Import complete! Run 'terraform plan' to verify."
