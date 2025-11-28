#!/bin/bash
# Import existing GCP resources into Terraform state for staging environment
# Run this script when resources already exist in GCP but not in Terraform state

set -e

PROJECT_ID="gen-lang-client-0805519538"
ENVIRONMENT="staging"

echo "🔄 Importing existing GCP resources into Terraform state for $ENVIRONMENT..."

# Navigate to terraform directory
cd "$(dirname "$0")"

# Initialize Terraform
echo "Initializing Terraform..."
terraform init \
  -backend-config="bucket=lordmuffin-maestro-tfstate" \
  -backend-config="prefix=terraform/state/$ENVIRONMENT"

# Select workspace
echo "Selecting workspace: $ENVIRONMENT"
terraform workspace select $ENVIRONMENT || terraform workspace new $ENVIRONMENT

# Import Firestore database
echo "Importing Firestore database..."
terraform import google_firestore_database.database "projects/$PROJECT_ID/databases/(default)" || echo "⚠️ Firestore database import failed (may already be in state)"

# Import storage bucket
echo "Importing storage bucket..."
terraform import google_storage_bucket.function_bucket "$PROJECT_ID-v2v2b-function-source" || echo "⚠️ Storage bucket import failed (may already be in state)"

# Import service account
echo "Importing service account..."
terraform import google_service_account.function_sa "projects/$PROJECT_ID/serviceAccounts/v2v2b-interrogator-staging-sa@$PROJECT_ID.iam.gserviceaccount.com" || echo "⚠️ Service account import failed (may already be in state)"

echo "✅ Import complete! Run 'terraform plan' to verify."
