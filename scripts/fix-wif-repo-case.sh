#!/bin/bash
set -e

# Fix WIF attribute condition to match actual repo case: lordmuffin/Maestro (capital M)

PROJECT_ID="gen-lang-client-0805519538"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
POOL_NAME="github-pool"
CORRECT_REPO="lordmuffin/Maestro"  # Capital M

echo "Fixing WIF providers for project $PROJECT_ID..."
echo "Project number: $PROJECT_NUMBER"
echo "Correct repository: $CORRECT_REPO"
echo ""

# Update github-staging provider
echo "1. Updating github-staging provider..."
gcloud iam workload-identity-pools providers update-oidc github-staging \
  --location="global" \
  --workload-identity-pool="$POOL_NAME" \
  --attribute-condition="assertion.repository=='$CORRECT_REPO'" \
  --project="$PROJECT_ID"
echo "✅ Updated github-staging provider"
echo ""

# Update github-readonly provider
echo "2. Updating github-readonly provider..."
gcloud iam workload-identity-pools providers update-oidc github-readonly \
  --location="global" \
  --workload-identity-pool="$POOL_NAME" \
  --attribute-condition="assertion.repository=='$CORRECT_REPO'" \
  --project="$PROJECT_ID"
echo "✅ Updated github-readonly provider"
echo ""

# Update github-actions provider (if exists)
echo "3. Checking for github-actions provider..."
if gcloud iam workload-identity-pools providers describe github-actions \
  --location="global" \
  --workload-identity-pool="$POOL_NAME" \
  --project="$PROJECT_ID" &>/dev/null; then

  echo "   Updating github-actions provider..."
  gcloud iam workload-identity-pools providers update-oidc github-actions \
    --location="global" \
    --workload-identity-pool="$POOL_NAME" \
    --attribute-condition="assertion.repository=='$CORRECT_REPO'" \
    --project="$PROJECT_ID"
  echo "✅ Updated github-actions provider"
else
  echo "⚠️  github-actions provider not found, skipping"
fi
echo ""

echo "🎉 All WIF providers updated successfully!"
echo ""
echo "The attribute condition now expects: $CORRECT_REPO"
echo ""
echo "Next steps:"
echo "1. Re-run your failed GitHub Actions workflow"
echo "2. The authentication should now succeed"
