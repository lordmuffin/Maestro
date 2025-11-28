# Fix WIF attribute condition to match actual repo case: lordmuffin/Maestro (capital M)

$ErrorActionPreference = "Stop"

$PROJECT_ID = "gen-lang-client-0805519538"
$PROJECT_NUMBER = (gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
$POOL_NAME = "github-pool"
$CORRECT_REPO = "lordmuffin/Maestro"  # Capital M

Write-Host "Fixing WIF providers for project $PROJECT_ID..." -ForegroundColor Cyan
Write-Host "Project number: $PROJECT_NUMBER"
Write-Host "Correct repository: $CORRECT_REPO"
Write-Host ""

# Update github-staging provider
Write-Host "1. Updating github-staging provider..." -ForegroundColor Yellow
gcloud iam workload-identity-pools providers update-oidc github-staging `
  --location="global" `
  --workload-identity-pool="$POOL_NAME" `
  --attribute-condition="assertion.repository=='$CORRECT_REPO'" `
  --project="$PROJECT_ID"
Write-Host "✅ Updated github-staging provider" -ForegroundColor Green
Write-Host ""

# Update github-readonly provider
Write-Host "2. Updating github-readonly provider..." -ForegroundColor Yellow
gcloud iam workload-identity-pools providers update-oidc github-readonly `
  --location="global" `
  --workload-identity-pool="$POOL_NAME" `
  --attribute-condition="assertion.repository=='$CORRECT_REPO'" `
  --project="$PROJECT_ID"
Write-Host "✅ Updated github-readonly provider" -ForegroundColor Green
Write-Host ""

# Update github-actions provider (if exists)
Write-Host "3. Checking for github-actions provider..." -ForegroundColor Yellow
try {
    $null = gcloud iam workload-identity-pools providers describe github-actions `
        --location="global" `
        --workload-identity-pool="$POOL_NAME" `
        --project="$PROJECT_ID" 2>&1

    Write-Host "   Updating github-actions provider..."
    gcloud iam workload-identity-pools providers update-oidc github-actions `
        --location="global" `
        --workload-identity-pool="$POOL_NAME" `
        --attribute-condition="assertion.repository=='$CORRECT_REPO'" `
        --project="$PROJECT_ID"
    Write-Host "✅ Updated github-actions provider" -ForegroundColor Green
} catch {
    Write-Host "⚠️  github-actions provider not found, skipping" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "🎉 All WIF providers updated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "The attribute condition now expects: $CORRECT_REPO"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Re-run your failed GitHub Actions workflow"
Write-Host "2. The authentication should now succeed"
