# GitOps Setup Guide - Manual Configuration Steps

This guide documents the manual GitHub repository configuration required after the code changes are merged.

## ⚠️ IMPORTANT: Order of Operations

**DO NOT enable branch protection until AFTER:**
1. The `develop` branch exists in the remote repository
2. All new GitHub Actions workflows are merged
3. GitHub Environments are configured with secrets

Otherwise, you'll lock yourself out!

---

## Phase 1: Branch Protection Rules

### Prerequisites
- `develop` branch pushed to remote: `git push origin develop`
- All new workflows merged to `main` and `develop`

### Step 1: Configure Branch Protection for `main`

1. Navigate to: `https://github.com/lordmuffin/maestro/settings/branches`
2. Click **"Add branch protection rule"**
3. Configure as follows:

**Branch name pattern:** `main`

**Protect matching branches:**
- ☑ **Require a pull request before merging**
  - Required approvals: **1**
  - ☑ Dismiss stale pull request approvals when new commits are pushed
  - ☑ Require review from Code Owners
  - ☑ Require approval of the most recent reviewable push

- ☑ **Require status checks to pass before merging**
  - ☑ Require branches to be up to date before merging
  - **Required status checks** (add after first PR runs):
    - `code-quality / Terraform Format Check`
    - `security-scan / Checkov Security Scan`
    - `security-scan / tfsec Security Scan`
    - `terraform-plan / Plan Terraform`

- ☑ **Require conversation resolution before merging**

- ☑ **Require linear history**

- ☑ **Require deployments to succeed before merging**
  - Environment name: `production`

- ☑ **Do not allow bypassing the above settings**

- ☑ **Rules applied to administrators**: YES

- ☐ **Allow force pushes**: NO

- ☐ **Allow deletions**: NO

4. Click **"Create"**

### Step 2: Configure Branch Protection for `develop`

1. Click **"Add branch protection rule"** again
2. Configure as follows:

**Branch name pattern:** `develop`

**Protect matching branches:**
- ☑ **Require a pull request before merging**
  - Required approvals: **1**
  - ☑ Require review from Code Owners

- ☑ **Require status checks to pass before merging**
  - **Required status checks**:
    - `code-quality / Terraform Format Check`
    - `security-scan / Checkov Security Scan`
    - `security-scan / tfsec Security Scan`
    - `terraform-plan / Plan Terraform`

- ☑ **Require conversation resolution before merging**

- ☑ **Require deployments to succeed before merging**
  - Environment name: `staging`

- ☑ **Rules applied to administrators**: YES

3. Click **"Create"**

---

## Phase 2: GitHub Environments Configuration

### Step 1: Create `terraform-plan` Environment (Read-Only)

1. Navigate to: `https://github.com/lordmuffin/maestro/settings/environments`
2. Click **"New environment"**
3. Name: `terraform-plan`
4. Click **"Configure environment"**

**Environment protection rules:**
- ☐ Required reviewers: (none)
- ☐ Deployment branches: All branches

**Environment secrets** (click "Add secret"):
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: (read-only service account WIF provider)
  ```
  projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-readonly
  ```
- `GCP_SERVICE_ACCOUNT`: `terraform-plan-readonly@gen-lang-client-0805519538.iam.gserviceaccount.com`

**Environment variables** (click "Add variable"):
- `TERRAFORM_STATE_BUCKET`: `project-maestro-tfstate`

5. Click **"Save protection rules"**

### Step 2: Create `staging` Environment

1. Click **"New environment"**
2. Name: `staging`
3. Click **"Configure environment"**

**Environment protection rules:**
- ☐ Required reviewers: (none - auto-deploy)
- ☑ **Deployment branches**: Selected branches
  - Add branch: `develop`

**Environment secrets:**
- `GCP_PROJECT_ID`: `gen-lang-client-0805519538`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: (staging WIF provider)
  ```
  projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-staging
  ```
- `GCP_SERVICE_ACCOUNT`: `terraform-staging@gen-lang-client-0805519538.iam.gserviceaccount.com`
- `TELEGRAM_BOT_TOKEN`: (staging bot token, or reuse production for testing)
- `GH_TOKEN_MAESTRO`: (GitHub token for maestro repo)
- `GH_TOKEN_BEYOND`: (GitHub token for beyond repo)

**Environment variables:**
- `TERRAFORM_STATE_BUCKET`: `project-maestro-tfstate`
- `NOTIFICATION_EMAIL`: `dorkmeisterx69@gmail.com`

5. Click **"Save protection rules"**

### Step 3: Create `production` Environment

1. Click **"New environment"**
2. Name: `production`
3. Click **"Configure environment"**

**Environment protection rules:**
- ☑ **Required reviewers**: 1
  - Select reviewer: `lordmuffin`
- ☑ **Deployment branches**: Selected branches
  - Add branch: `main`
- **Wait timer**: 0 minutes (immediate after approval)

**Environment secrets** (copy from existing `gen-lang-client-0805519538` environment):
- `GCP_PROJECT_ID`: `gen-lang-client-0805519538`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: (production WIF provider)
- `GCP_SERVICE_ACCOUNT`: (production service account)
- `TELEGRAM_BOT_TOKEN`: (production bot token)
- `GH_TOKEN_MAESTRO`: (GitHub token)
- `GH_TOKEN_BEYOND`: (GitHub token)

**Environment variables:**
- `TERRAFORM_STATE_BUCKET`: `project-maestro-tfstate`
- `NOTIFICATION_EMAIL`: `dorkmeisterx69@gmail.com`

5. Click **"Save protection rules"**

---

## Phase 3: GCP Prerequisites

### Service Accounts to Create

#### 1. Staging Service Account
```bash
# Create service account
gcloud iam service-accounts create terraform-staging \
  --display-name="Terraform Staging Deployer" \
  --project=gen-lang-client-0805519538

# Grant required roles
gcloud projects add-iam-policy-binding gen-lang-client-0805519538 \
  --member="serviceAccount:terraform-staging@gen-lang-client-0805519538.iam.gserviceaccount.com" \
  --role="roles/editor"

gcloud projects add-iam-policy-binding gen-lang-client-0805519538 \
  --member="serviceAccount:terraform-staging@gen-lang-client-0805519538.iam.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageAdmin"

gcloud projects add-iam-policy-binding gen-lang-client-0805519538 \
  --member="serviceAccount:terraform-staging@gen-lang-client-0805519538.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountAdmin"
```

#### 2. Read-Only Service Account (for plan-only)
```bash
# Create service account
gcloud iam service-accounts create terraform-plan-readonly \
  --display-name="Terraform Plan Read-Only" \
  --project=gen-lang-client-0805519538

# Grant viewer role (read-only)
gcloud projects add-iam-policy-binding gen-lang-client-0805519538 \
  --member="serviceAccount:terraform-plan-readonly@gen-lang-client-0805519538.iam.gserviceaccount.com" \
  --role="roles/viewer"

# Grant state bucket read access
gsutil iam ch \
  serviceAccount:terraform-plan-readonly@gen-lang-client-0805519538.iam.gserviceaccount.com:objectViewer \
  gs://project-maestro-tfstate
```

### Workload Identity Federation Setup

#### For Staging
```bash
# Create workload identity pool (if not exists)
gcloud iam workload-identity-pools create github \
  --location="global" \
  --display-name="GitHub Actions" \
  --project=gen-lang-client-0805519538

# Create provider for staging
gcloud iam workload-identity-pools providers create-oidc github-staging \
  --location="global" \
  --workload-identity-pool="github" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" \
  --attribute-condition="assertion.repository=='lordmuffin/maestro'" \
  --project=gen-lang-client-0805519538

# Bind service account to GitHub
gcloud iam service-accounts add-iam-policy-binding \
  terraform-staging@gen-lang-client-0805519538.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/lordmuffin/maestro" \
  --project=gen-lang-client-0805519538
```

#### For Read-Only (Plan)
```bash
# Create provider for plan
gcloud iam workload-identity-pools providers create-oidc github-plan \
  --location="global" \
  --workload-identity-pool="github" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='lordmuffin/maestro'" \
  --project=gen-lang-client-0805519538

# Bind read-only service account
gcloud iam service-accounts add-iam-policy-binding \
  terraform-plan-readonly@gen-lang-client-0805519538.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/lordmuffin/maestro" \
  --project=gen-lang-client-0805519538
```

### Enable GCS State Versioning
```bash
# Enable versioning for rollback capability
gsutil versioning set on gs://project-maestro-tfstate

# Verify
gsutil versioning get gs://project-maestro-tfstate
```

---

## Phase 4: Additional GitHub Secrets

### Repository-Level Secrets

1. Navigate to: `https://github.com/lordmuffin/maestro/settings/secrets/actions`
2. Add the following secrets:

**`EMAIL_APP_PASSWORD`**
- Go to: https://myaccount.google.com/apppasswords
- Generate app password for "Maestro GitOps"
- Copy and paste into GitHub secret

---

## Phase 5: Enable State Versioning (Local Testing)

```bash
# Navigate to terraform directory
cd terraform

# Initialize with bucket
terraform init -backend-config="bucket=project-maestro-tfstate"

# Create workspaces
terraform workspace new staging
terraform workspace new production

# Verify
terraform workspace list

# Test staging
terraform workspace select staging
terraform plan -var-file=environments/staging.tfvars

# Test production
terraform workspace select production
terraform plan -var-file=environments/production.tfvars
```

---

## Validation Checklist

### After Setup, Verify:

- [ ] `develop` branch exists in remote
- [ ] Branch protection active on `main` (try direct commit - should fail)
- [ ] Branch protection active on `develop` (try direct commit - should fail)
- [ ] Three environments exist: `terraform-plan`, `staging`, `production`
- [ ] `production` environment requires manual approval
- [ ] `staging` environment only allows deployment from `develop`
- [ ] `production` environment only allows deployment from `main`
- [ ] All environment secrets populated (check each environment)
- [ ] GCS state versioning enabled
- [ ] Terraform workspaces created locally
- [ ] Can run `terraform plan` in both workspaces

### Test Workflow:

1. Create feature branch: `git checkout -b feature/test-gitops`
2. Make small change (e.g., add comment to README)
3. Commit and push
4. Create PR to `develop`
5. Verify:
   - ✅ Terraform plan runs
   - ✅ Security scans run
   - ✅ PR requires approval
   - ✅ Cannot merge without approval
6. Approve and merge
7. Verify staging deployment triggers automatically

---

## Troubleshooting

### Issue: Status checks not appearing

**Solution:** Status checks only appear after the workflow has run at least once. Create a test PR to trigger all workflows, then add the status check names to branch protection.

### Issue: Cannot push to develop

**Solution:** You may have enabled branch protection too early. Temporarily disable protection, push the branch, then re-enable.

### Issue: Workload Identity Federation authentication fails

**Solution:**
1. Verify PROJECT_NUMBER is correct (not PROJECT_ID)
2. Check attribute condition matches repository exactly
3. Ensure service account has `workloadIdentityUser` role binding

### Issue: Terraform plan fails with "permission denied"

**Solution:** Read-only service account needs `roles/viewer` AND explicit `objectViewer` on state bucket.

---

## Next Steps

After completing this setup:

1. ✅ All manual GitHub configurations complete
2. ✅ GCP service accounts and WIF configured
3. ✅ Terraform workspaces tested locally
4. 🚀 Ready to test full GitOps workflow (see plan Phase 7)

---

**Last Updated:** 2025-11-26
**Plan Reference:** `.claude/plans/pure-napping-sun.md`
