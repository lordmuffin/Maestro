# GCP Infrastructure Setup for GitOps (PowerShell)
# This script creates service accounts and Workload Identity Federation for GitHub Actions

# Configuration
$PROJECT_ID = "gen-lang-client-0805519538"
$GITHUB_REPO = "lordmuffin/maestro"
$STATE_BUCKET = "lordmuffin-maestro-tfstate"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "GitOps GCP Infrastructure Setup" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Project: " -NoNewline -ForegroundColor Yellow
Write-Host $PROJECT_ID
Write-Host "GitHub Repo: " -NoNewline -ForegroundColor Yellow
Write-Host $GITHUB_REPO
Write-Host "State Bucket: " -NoNewline -ForegroundColor Yellow
Write-Host $STATE_BUCKET
Write-Host ""

# Get project number
Write-Host "[1/7] Getting project number..." -ForegroundColor Blue
$PROJECT_NUMBER = (gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to get project number" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Project Number: $PROJECT_NUMBER" -ForegroundColor Green
Write-Host ""

# Step 1: Create Staging Service Account
Write-Host "[2/7] Creating Staging Service Account..." -ForegroundColor Blue
$stagingSA = "terraform-staging@$PROJECT_ID.iam.gserviceaccount.com"
$null = gcloud iam service-accounts describe $stagingSA --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠ Service account terraform-staging already exists" -ForegroundColor Yellow
} else {
    $null = gcloud iam service-accounts create terraform-staging `
        --display-name="Terraform Staging Deployer" `
        --project=$PROJECT_ID 2>&1
    Write-Host "✓ Created terraform-staging service account" -ForegroundColor Green
}

Write-Host "  Granting IAM roles..."
$null = gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$stagingSA" `
    --role="roles/editor" `
    --condition=None `
    --quiet 2>&1

$null = gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$stagingSA" `
    --role="roles/serviceusage.serviceUsageAdmin" `
    --condition=None `
    --quiet 2>&1

$null = gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$stagingSA" `
    --role="roles/iam.serviceAccountAdmin" `
    --condition=None `
    --quiet 2>&1

Write-Host "✓ Staging service account configured" -ForegroundColor Green
Write-Host ""

# Step 2: Create Read-Only Service Account
Write-Host "[3/7] Creating Read-Only Service Account (for plan)..." -ForegroundColor Blue
$readonlySA = "terraform-plan-readonly@$PROJECT_ID.iam.gserviceaccount.com"
$null = gcloud iam service-accounts describe $readonlySA --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠ Service account terraform-plan-readonly already exists" -ForegroundColor Yellow
} else {
    $null = gcloud iam service-accounts create terraform-plan-readonly `
        --display-name="Terraform Plan Read-Only" `
        --project=$PROJECT_ID 2>&1
    Write-Host "✓ Created terraform-plan-readonly service account" -ForegroundColor Green
}

Write-Host "  Granting IAM roles..."
$null = gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$readonlySA" `
    --role="roles/viewer" `
    --condition=None `
    --quiet 2>&1

Write-Host "  Granting state bucket access..."
$null = gsutil iam ch "serviceAccount:${readonlySA}:objectViewer" "gs://$STATE_BUCKET" 2>&1

Write-Host "✓ Read-only service account configured" -ForegroundColor Green
Write-Host ""

# Step 3: Create Workload Identity Pool
Write-Host "[4/7] Creating Workload Identity Pool..." -ForegroundColor Blue
$null = gcloud iam workload-identity-pools describe github --location="global" --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠ Workload identity pool 'github' already exists" -ForegroundColor Yellow
} else {
    $null = gcloud iam workload-identity-pools create github `
        --location="global" `
        --display-name="GitHub Actions" `
        --project=$PROJECT_ID 2>&1
    Write-Host "✓ Created workload identity pool" -ForegroundColor Green
}
Write-Host ""

# Step 4: Create WIF Provider for Staging
Write-Host "[5/7] Creating WIF Provider for Staging..." -ForegroundColor Blue
$null = gcloud iam workload-identity-pools providers describe github-staging `
    --location="global" `
    --workload-identity-pool="github" `
    --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠ Provider 'github-staging' already exists" -ForegroundColor Yellow
} else {
    $null = gcloud iam workload-identity-pools providers create-oidc github-staging `
        --location="global" `
        --workload-identity-pool="github" `
        --issuer-uri="https://token.actions.githubusercontent.com" `
        --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" `
        --attribute-condition="assertion.repository=='$GITHUB_REPO'" `
        --project=$PROJECT_ID 2>&1
    Write-Host "✓ Created github-staging provider" -ForegroundColor Green
}

Write-Host "  Binding service account..."
$null = gcloud iam service-accounts add-iam-policy-binding $stagingSA `
    --role="roles/iam.workloadIdentityUser" `
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$GITHUB_REPO" `
    --project=$PROJECT_ID `
    --quiet 2>&1

Write-Host "✓ Staging WIF configured" -ForegroundColor Green
Write-Host ""

# Step 5: Create WIF Provider for Plan (Read-Only)
Write-Host "[6/7] Creating WIF Provider for Plan (Read-Only)..." -ForegroundColor Blue
$null = gcloud iam workload-identity-pools providers describe github-readonly `
    --location="global" `
    --workload-identity-pool="github" `
    --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠ Provider 'github-readonly' already exists" -ForegroundColor Yellow
} else {
    $null = gcloud iam workload-identity-pools providers create-oidc github-readonly `
        --location="global" `
        --workload-identity-pool="github" `
        --issuer-uri="https://token.actions.githubusercontent.com" `
        --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" `
        --attribute-condition="assertion.repository=='$GITHUB_REPO'" `
        --project=$PROJECT_ID 2>&1
    Write-Host "✓ Created github-readonly provider" -ForegroundColor Green
}

Write-Host "  Binding service account..."
$null = gcloud iam service-accounts add-iam-policy-binding $readonlySA `
    --role="roles/iam.workloadIdentityUser" `
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$GITHUB_REPO" `
    --project=$PROJECT_ID `
    --quiet 2>&1

Write-Host "✓ Plan WIF configured" -ForegroundColor Green
Write-Host ""

# Step 6: Enable State Versioning
Write-Host "[7/7] Enabling GCS State Versioning..." -ForegroundColor Blue
$versioningStatus = gsutil versioning get "gs://$STATE_BUCKET" 2>&1
if ($versioningStatus -match "Enabled") {
    Write-Host "⚠ Versioning already enabled on $STATE_BUCKET" -ForegroundColor Yellow
} else {
    $null = gsutil versioning set on "gs://$STATE_BUCKET" 2>&1
    Write-Host "✓ Enabled versioning on $STATE_BUCKET" -ForegroundColor Green
}
Write-Host ""

# Summary Output
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 GitHub Secrets Configuration Values:" -ForegroundColor Blue
Write-Host ""
Write-Host "For terraform-plan environment:" -ForegroundColor Yellow
Write-Host "  GCP_WORKLOAD_IDENTITY_PROVIDER: projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-readonly"
Write-Host "  GCP_SERVICE_ACCOUNT: $readonlySA"
Write-Host ""
Write-Host "For staging environment:" -ForegroundColor Yellow
Write-Host "  GCP_WORKLOAD_IDENTITY_PROVIDER: projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-staging"
Write-Host "  GCP_SERVICE_ACCOUNT: $stagingSA"
Write-Host "  GCP_PROJECT_ID: $PROJECT_ID"
Write-Host ""
Write-Host "For production environment (reuse existing 'gen-lang-client-0805519538'):" -ForegroundColor Yellow
Write-Host "  Copy secrets from existing environment"
Write-Host ""
Write-Host "Environment variables (all environments):" -ForegroundColor Yellow
Write-Host "  TERRAFORM_STATE_BUCKET: $STATE_BUCKET"
Write-Host "  NOTIFICATION_EMAIL: dorkmeisterx69@gmail.com"
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Blue
Write-Host "1. Navigate to: https://github.com/$GITHUB_REPO/settings/environments"
Write-Host "2. Create three environments: terraform-plan, staging, production"
Write-Host "3. Add the secrets and variables above to each environment"
Write-Host "4. See QUICK_SETUP.md for detailed configuration"
Write-Host ""
