#!/bin/bash
# GCP Infrastructure Setup for GitOps
# This script creates service accounts and Workload Identity Federation for GitHub Actions
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Project: project-maestro-gcp
# - User must have Project IAM Admin role

set -e  # Exit on any error

# Configuration
PROJECT_ID="gen-lang-client-0805519538"
GITHUB_REPO="lordmuffin/maestro"
STATE_BUCKET="lordmuffin-maestro-tfstate"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}GitOps GCP Infrastructure Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Project:${NC} $PROJECT_ID"
echo -e "${YELLOW}GitHub Repo:${NC} $GITHUB_REPO"
echo -e "${YELLOW}State Bucket:${NC} $STATE_BUCKET"
echo ""

# Get project number
echo -e "${BLUE}[1/7] Getting project number...${NC}"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
echo -e "${GREEN}✓ Project Number: $PROJECT_NUMBER${NC}"
echo ""

# Step 1: Create Staging Service Account
echo -e "${BLUE}[2/7] Creating Staging Service Account...${NC}"
if gcloud iam service-accounts describe "terraform-staging@$PROJECT_ID.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${YELLOW}⚠ Service account terraform-staging already exists${NC}"
else
    gcloud iam service-accounts create terraform-staging \
        --display-name="Terraform Staging Deployer" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created terraform-staging service account${NC}"
fi

echo "  Granting IAM roles..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:terraform-staging@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/editor" \
    --condition=None \
    --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:terraform-staging@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/serviceusage.serviceUsageAdmin" \
    --condition=None \
    --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:terraform-staging@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountAdmin" \
    --condition=None \
    --quiet

echo -e "${GREEN}✓ Staging service account configured${NC}"
echo ""

# Step 2: Create Read-Only Service Account
echo -e "${BLUE}[3/7] Creating Read-Only Service Account (for plan)...${NC}"
if gcloud iam service-accounts describe "terraform-plan-readonly@$PROJECT_ID.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${YELLOW}⚠ Service account terraform-plan-readonly already exists${NC}"
else
    gcloud iam service-accounts create terraform-plan-readonly \
        --display-name="Terraform Plan Read-Only" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created terraform-plan-readonly service account${NC}"
fi

echo "  Granting IAM roles..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:terraform-plan-readonly@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/viewer" \
    --condition=None \
    --quiet

echo "  Granting state bucket access..."
gsutil iam ch \
    "serviceAccount:terraform-plan-readonly@$PROJECT_ID.iam.gserviceaccount.com:objectViewer" \
    "gs://$STATE_BUCKET"

echo -e "${GREEN}✓ Read-only service account configured${NC}"
echo ""

# Step 3: Create Workload Identity Pool
echo -e "${BLUE}[4/7] Creating Workload Identity Pool...${NC}"
if gcloud iam workload-identity-pools describe github --location="global" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${YELLOW}⚠ Workload identity pool 'github' already exists${NC}"
else
    gcloud iam workload-identity-pools create github \
        --location="global" \
        --display-name="GitHub Actions" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created workload identity pool${NC}"
fi
echo ""

# Step 4: Create WIF Provider for Staging
echo -e "${BLUE}[5/7] Creating WIF Provider for Staging...${NC}"
if gcloud iam workload-identity-pools providers describe github-staging \
    --location="global" \
    --workload-identity-pool="github" \
    --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${YELLOW}⚠ Provider 'github-staging' already exists${NC}"
else
    gcloud iam workload-identity-pools providers create-oidc github-staging \
        --location="global" \
        --workload-identity-pool="github" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" \
        --attribute-condition="assertion.repository=='$GITHUB_REPO'" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created github-staging provider${NC}"
fi

echo "  Binding service account..."
gcloud iam service-accounts add-iam-policy-binding \
    "terraform-staging@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$GITHUB_REPO" \
    --project="$PROJECT_ID" \
    --quiet

echo -e "${GREEN}✓ Staging WIF configured${NC}"
echo ""

# Step 5: Create WIF Provider for Plan (Read-Only)
echo -e "${BLUE}[6/7] Creating WIF Provider for Plan (Read-Only)...${NC}"
if gcloud iam workload-identity-pools providers describe github-readonly \
    --location="global" \
    --workload-identity-pool="github" \
    --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${YELLOW}⚠ Provider 'github-readonly' already exists${NC}"
else
    gcloud iam workload-identity-pools providers create-oidc github-readonly \
        --location="global" \
        --workload-identity-pool="github" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
        --attribute-condition="assertion.repository=='$GITHUB_REPO'" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created github-readonly provider${NC}"
fi

echo "  Binding service account..."
gcloud iam service-accounts add-iam-policy-binding \
    "terraform-plan-readonly@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$GITHUB_REPO" \
    --project="$PROJECT_ID" \
    --quiet

echo -e "${GREEN}✓ Plan WIF configured${NC}"
echo ""

# Step 6: Enable State Versioning
echo -e "${BLUE}[7/7] Enabling GCS State Versioning...${NC}"
CURRENT_VERSIONING=$(gsutil versioning get "gs://$STATE_BUCKET" | grep -o "Enabled" || echo "Disabled")
if [ "$CURRENT_VERSIONING" = "Enabled" ]; then
    echo -e "${YELLOW}⚠ Versioning already enabled on $STATE_BUCKET${NC}"
else
    gsutil versioning set on "gs://$STATE_BUCKET"
    echo -e "${GREEN}✓ Enabled versioning on $STATE_BUCKET${NC}"
fi
echo ""

# Summary Output
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📋 GitHub Secrets Configuration Values:${NC}"
echo ""
echo -e "${YELLOW}For terraform-plan environment:${NC}"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER: projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-readonly"
echo "  GCP_SERVICE_ACCOUNT: terraform-plan-readonly@$PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo -e "${YELLOW}For staging environment:${NC}"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER: projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-staging"
echo "  GCP_SERVICE_ACCOUNT: terraform-staging@$PROJECT_ID.iam.gserviceaccount.com"
echo "  GCP_PROJECT_ID: $PROJECT_ID"
echo ""
echo -e "${YELLOW}For production environment (existing):${NC}"
echo "  GCP_PROJECT_ID: $PROJECT_ID"
echo "  Use existing production service account and WIF provider"
echo ""
echo -e "${YELLOW}Environment variables (all environments):${NC}"
echo "  TERRAFORM_STATE_BUCKET: $STATE_BUCKET"
echo "  NOTIFICATION_EMAIL: dorkmeisterx69@gmail.com"
echo ""
echo -e "${BLUE}📝 Next Steps:${NC}"
echo "1. Navigate to: https://github.com/$GITHUB_REPO/settings/environments"
echo "2. Create three environments: terraform-plan, staging, production"
echo "3. Add the secrets and variables above to each environment"
echo "4. See GITOPS_SETUP_GUIDE.md Phase 2 for detailed configuration"
echo ""
echo -e "${BLUE}🔧 Verification:${NC}"
echo "Run: gcloud iam service-accounts list --project=$PROJECT_ID"
echo "Run: gcloud iam workload-identity-pools providers list --workload-identity-pool=github --location=global --project=$PROJECT_ID"
echo ""
