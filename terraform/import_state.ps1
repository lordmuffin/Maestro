param(
    [string]$ProjectId = "project-maestro-gcp",
    [string]$Region = "us-central1"
)

$ErrorActionPreference = "Continue"

# Ensure we are in the script's directory
Set-Location $PSScriptRoot

# Select production workspace
Write-Host "Selecting production workspace..."
terraform workspace select production

Write-Host "Importing resources for project: $ProjectId"

# Import Service Account
Write-Host "Importing Service Account..."
terraform import google_service_account.function_sa "projects/$ProjectId/serviceAccounts/v2v2b-interrogator-sa@$ProjectId.iam.gserviceaccount.com"

# Import Cloud Function (Gen 2)
Write-Host "Importing Cloud Function..."
terraform import google_cloudfunctions2_function.v2v2b_interrogator "projects/$ProjectId/locations/$Region/functions/v2v2b-interrogator"

Write-Host "Import process finished. Please check for any errors above."
