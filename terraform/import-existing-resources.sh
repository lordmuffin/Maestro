#!/bin/bash
# Script to import existing GCP resources into Terraform state
# Run this locally or in GitHub Actions to sync existing resources

set -e

PROJECT_ID="${1:-gen-lang-client-0805519538}"
REGION="${2:-us-central1}"
FUNCTION_NAME="${3:-v2v2b-interrogator}"

echo "Importing existing resources for project: $PROJECT_ID"

# Import Firestore database
echo "Importing Firestore database..."
terraform import google_firestore_database.database "projects/$PROJECT_ID/databases/(default)" || echo "Already imported or doesn't exist"

# Import Storage bucket
echo "Importing Storage bucket..."
terraform import google_storage_bucket.function_bucket "$PROJECT_ID-v2v2b-function-source" || echo "Already imported or doesn't exist"

# Import Service account
echo "Importing Service account..."
terraform import google_service_account.function_sa "projects/$PROJECT_ID/serviceAccounts/$FUNCTION_NAME-sa@$PROJECT_ID.iam.gserviceaccount.com" || echo "Already imported or doesn't exist"

# Import API services
echo "Importing API services..."
terraform import google_project_service.cloud_functions "$PROJECT_ID/cloudfunctions.googleapis.com" || echo "Already imported"
terraform import google_project_service.cloud_build "$PROJECT_ID/cloudbuild.googleapis.com" || echo "Already imported"
terraform import google_project_service.firestore "$PROJECT_ID/firestore.googleapis.com" || echo "Already imported"
terraform import google_project_service.aiplatform "$PROJECT_ID/aiplatform.googleapis.com" || echo "Already imported"
terraform import google_project_service.chat "$PROJECT_ID/chat.googleapis.com" || echo "Already imported"
terraform import google_project_service.cloud_run "$PROJECT_ID/run.googleapis.com" || echo "Already imported"

echo "Import complete! Run 'terraform plan' to verify."
