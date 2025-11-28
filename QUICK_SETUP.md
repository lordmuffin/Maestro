# Quick Setup Guide - GitOps Fix

This guide will get your GitOps workflow operational in ~15 minutes.

## Current Issue

The staging workflow is failing because GitHub Environments aren't configured yet:
```
Error: the GitHub Action workflow must specify exactly one of "workload_identity_provider" or "credentials_json"
```

## Solution Overview

1. Run GCP setup script (5 min)
2. Configure GitHub Environments (10 min)
3. Re-run failed workflow

---

## Step 1: Run GCP Setup Script

Open PowerShell and run:

```powershell
cd c:\Users\andre\Github\Maestro
.\scripts\setup-gcp-infrastructure.ps1
```

**What this does:**
- Creates `terraform-staging` service account
- Creates `terraform-plan-readonly` service account
- Sets up Workload Identity Federation
- Enables GCS state versioning

**Output:** The script will display all the values you need for GitHub Environments configuration.

💡 **Tip:** Copy the output to a text file - you'll need these values in Step 2.

---

## Step 2: Configure GitHub Environments

### A. Create `terraform-plan` Environment

1. Navigate to: https://github.com/lordmuffin/maestro/settings/environments
2. Click **"New environment"**
3. Name: `terraform-plan`
4. Click **"Configure environment"**

**Add Environment Secrets:**
- Click "Add secret" for each:
  - `GCP_WORKLOAD_IDENTITY_PROVIDER`: (copy from script output - github-readonly provider)
  - `GCP_SERVICE_ACCOUNT`: `terraform-plan-readonly@gen-lang-client-0805519538.iam.gserviceaccount.com`

**Add Environment Variables:**
- Click "Add variable":
  - `TERRAFORM_STATE_BUCKET`: `project-maestro-tfstate`

5. Click **"Save protection rules"**

### B. Create `staging` Environment

1. Click **"New environment"**
2. Name: `staging`
3. Click **"Configure environment"**

**Environment Protection Rules:**
- ☑ **Deployment branches**: Selected branches
  - Add branch: `develop`

**Add Environment Secrets:**
- Click "Add secret" for each:
  - `GCP_WORKLOAD_IDENTITY_PROVIDER`: (copy from script output - github-staging provider)
  - `GCP_SERVICE_ACCOUNT`: `terraform-staging@gen-lang-client-0805519538.iam.gserviceaccount.com`
  - `GCP_PROJECT_ID`: `gen-lang-client-0805519538`
  - `TELEGRAM_BOT_TOKEN`: (your existing token - copy from current secrets)
  - `GH_TOKEN_MAESTRO`: (your existing token - copy from current secrets)
  - `GH_TOKEN_BEYOND`: (your existing token - copy from current secrets)
  - `GOOGLE_DRIVE_FOLDER_ID`: (your existing folder ID - if you have one)
  - `EMAIL_APP_PASSWORD`: (create at https://myaccount.google.com/apppasswords)

**Add Environment Variables:**
- Click "Add variable" for each:
  - `TERRAFORM_STATE_BUCKET`: `project-maestro-tfstate`
  - `NOTIFICATION_EMAIL`: `dorkmeisterx69@gmail.com`
  - `OBSIDIAN_DRIVE_FOLDER_ID`: (your folder ID - if you have one)
  - `KANBAN_FOLDER_ID`: (your folder ID - if you have one)
  - `DRIVE_POLL_INTERVAL`: `300`
  - `FUNCTION_URL`: (leave empty for now)

5. Click **"Save protection rules"**

### C. Create `production` Environment

1. Click **"New environment"**
2. Name: `production`
3. Click **"Configure environment"**

**Environment Protection Rules:**
- ☑ **Required reviewers**: 1
  - Select yourself: `lordmuffin`
- ☑ **Deployment branches**: Selected branches
  - Add branch: `main`

**Add Environment Secrets:**
(Copy all secrets from your existing GitHub secrets OR from staging environment)
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: (use existing production WIF provider)
- `GCP_SERVICE_ACCOUNT`: (use existing production service account)
- `GCP_PROJECT_ID`: `gen-lang-client-0805519538`
- `TELEGRAM_BOT_TOKEN`: (production bot token)
- `GH_TOKEN_MAESTRO`: (same as staging)
- `GH_TOKEN_BEYOND`: (same as staging)
- `GOOGLE_DRIVE_FOLDER_ID`: (same as staging)
- `EMAIL_APP_PASSWORD`: (same as staging)

**Add Environment Variables:**
(Same as staging)
- `TERRAFORM_STATE_BUCKET`: `project-maestro-tfstate`
- `NOTIFICATION_EMAIL`: `dorkmeisterx69@gmail.com`
- `OBSIDIAN_DRIVE_FOLDER_ID`: (same as staging)
- `KANBAN_FOLDER_ID`: (same as staging)
- `DRIVE_POLL_INTERVAL`: `300`
- `FUNCTION_URL`: (leave empty for now)

5. Click **"Save protection rules"**

---

## Step 3: Re-run Failed Workflow

1. Navigate to: https://github.com/lordmuffin/maestro/actions
2. Find the failed "Apply to Staging" workflow
3. Click **"Re-run all jobs"**

**Expected outcome:**
- ✅ Workflow should now authenticate successfully
- ✅ Terraform should initialize with the state bucket
- ✅ Deployment should complete (or at least get past the auth error)

---

## Quick Checklist

- [ ] Ran `setup-gcp-infrastructure.ps1`
- [ ] Created `terraform-plan` environment with secrets
- [ ] Created `staging` environment with secrets
- [ ] Created `production` environment with secrets
- [ ] Re-ran failed workflow
- [ ] Workflow passed authentication step

---

## Troubleshooting

### Issue: Script fails with "permission denied"

**Solution:** Ensure you're authenticated with gcloud:
```powershell
gcloud auth login
gcloud config set project gen-lang-client-0805519538
```

### Issue: Can't find existing secrets to copy

**Solution:** Check repository secrets:
1. Go to: https://github.com/lordmuffin/maestro/settings/secrets/actions
2. Copy values from repository-level secrets to environment secrets

### Issue: Still getting auth error after setup

**Solution:** Double-check the WIF provider value:
- Must be in format: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-staging`
- Use PROJECT_NUMBER (numeric), not PROJECT_ID (string)

---

## After Successful Setup

Once the workflow passes:

1. **Test the full workflow:**
   - Create a small change in a feature branch
   - Push to `develop`
   - Verify staging auto-deploys

2. **Optional: Enable branch protection** (see GITOPS_SETUP_GUIDE.md Phase 1)
   - This is optional - you can continue without it
   - Branch protection adds PR approval requirements

---

**Last Updated:** 2025-11-26
**Related Files:**
- [GITOPS_SETUP_GUIDE.md](GITOPS_SETUP_GUIDE.md) - Full setup guide
- [GITOPS_IMPLEMENTATION.md](GITOPS_IMPLEMENTATION.md) - Implementation details
