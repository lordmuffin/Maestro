# GitHub Actions Configuration Guide

This guide explains how to configure GitHub secrets and environment variables for the Terraform deployment workflow.

## Overview

All Terraform variables are centralized in the GitHub Actions workflow using environment variables. This means you only need to configure values in one location: **GitHub Settings**.

## Required Configuration

### 1. GitHub Secrets

Navigate to: **Settings → Secrets and variables → Actions → Secrets**

#### Required Secrets:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `GCP_PROJECT_ID` | Your GCP project ID | `gen-lang-client-0805519538` |
| `GH_TOKEN` | GitHub Personal Access Token with `repo` scope | `ghp_xxxxxxxxxxxx` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider for authentication | `projects/123456/locations/global/workloadIdentityPools/github/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | Service account email for Workload Identity | `terraform-deployer@project.iam.gserviceaccount.com` |

#### Optional Secrets (Google Drive Integration):

| Secret Name | Description | Example |
|------------|-------------|---------|
| `GOOGLE_DRIVE_FOLDER_ID` | Drive folder ID to monitor for transcripts | `1abc123def456ghi789` |
| `OBSIDIAN_DRIVE_FOLDER_ID` | Drive folder ID for Obsidian vault | `1xyz987uvw654rst321` |

### 2. GitHub Variables

Navigate to: **Settings → Secrets and variables → Actions → Variables**

#### Optional Variables:

| Variable Name | Description | Default | Example |
|--------------|-------------|---------|---------|
| `REPO_NAME` | GitHub repository name | `lordmuffin/Maestro` | `username/repo` |
| `DRIVE_POLL_INTERVAL` | Drive scan interval in seconds | `300` | `300` |
| `FUNCTION_URL` | Cloud Function URL (populated after first deployment) | `""` | `https://...` |
| `TERRAFORM_STATE_BUCKET` | GCS bucket for Terraform state | - | `my-terraform-state` |

## How to Get Values

### GCP_PROJECT_ID
```bash
gcloud config get-value project
```

### GH_TOKEN (GitHub Personal Access Token)
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (full control of private repositories)
4. Copy the generated token (starts with `ghp_`)

### GOOGLE_DRIVE_FOLDER_ID
1. Open Google Drive in browser
2. Navigate to the folder you want to monitor
3. Copy the folder ID from the URL:
   ```
   https://drive.google.com/drive/folders/FOLDER_ID_HERE
                                          ^^^^^^^^^^^^^^^^
   ```

### GCP_WORKLOAD_IDENTITY_PROVIDER
Follow the [Workload Identity Federation setup guide](https://github.com/google-github-actions/auth#setting-up-workload-identity-federation).

```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github" \
  --project="PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions"

# Create Provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Get the full provider name
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github" \
  --format="value(name)"
```

### GCP_SERVICE_ACCOUNT
```bash
# Create service account
gcloud iam service-accounts create terraform-deployer \
  --display-name="Terraform Deployer for GitHub Actions"

# Get email
gcloud iam service-accounts list --filter="terraform-deployer"

# Grant required roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:terraform-deployer@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/editor"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:terraform-deployer@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageAdmin"

# Allow GitHub Actions to impersonate this service account
gcloud iam service-accounts add-iam-policy-binding \
  "terraform-deployer@PROJECT_ID.iam.gserviceaccount.com" \
  --project="PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/lordmuffin/Maestro"
```

## Configuration Steps

### Step 1: Add Required Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each required secret:
   - Name: `GCP_PROJECT_ID`
   - Value: Your GCP project ID
   - Click **Add secret**
5. Repeat for all required secrets

### Step 2: Add Optional Variables

1. In the same **Actions** page, click the **Variables** tab
2. Click **New repository variable**
3. Add variables as needed (all are optional with defaults)

### Step 3: Verify Configuration

After adding secrets, the workflow will validate them on each run:

```yaml
- name: Validate Required Configuration
  run: |
    if [ -z "$TF_VAR_gcp_project" ]; then
      echo "::error::GCP_PROJECT_ID secret is not set"
      exit 1
    fi
    # ... validates all required secrets
```

### Step 4: Test Deployment

Trigger a deployment to verify configuration:

```bash
# Option 1: Push to main branch
git push origin main

# Option 2: Manual workflow dispatch
# Go to Actions → Terraform Deploy → Run workflow
```

## Environment Variables Mapping

The workflow automatically maps GitHub secrets to Terraform variables:

| GitHub Secret/Variable | Terraform Variable | Purpose |
|----------------------|-------------------|---------|
| `GCP_PROJECT_ID` | `TF_VAR_gcp_project` | GCP project to deploy to |
| `GH_TOKEN` | `TF_VAR_github_token` | GitHub API authentication |
| `REPO_NAME` | `TF_VAR_repo_name` | Repository for PR creation |
| `GOOGLE_DRIVE_FOLDER_ID` | `TF_VAR_google_drive_folder_id` | Drive folder to monitor |
| `OBSIDIAN_DRIVE_FOLDER_ID` | `TF_VAR_obsidian_drive_folder_id` | Obsidian vault folder |
| `DRIVE_POLL_INTERVAL` | `TF_VAR_drive_poll_interval` | Polling interval (seconds) |
| `FUNCTION_URL` | `TF_VAR_function_url` | Cloud Function URL |

These are defined in the workflow's `env` section:

```yaml
env:
  TF_VAR_gcp_project: ${{ secrets.GCP_PROJECT_ID }}
  TF_VAR_github_token: ${{ secrets.GH_TOKEN }}
  TF_VAR_repo_name: ${{ vars.REPO_NAME || 'lordmuffin/Maestro' }}
  TF_VAR_google_drive_folder_id: ${{ secrets.GOOGLE_DRIVE_FOLDER_ID || '' }}
  TF_VAR_obsidian_drive_folder_id: ${{ secrets.OBSIDIAN_DRIVE_FOLDER_ID || '' }}
  TF_VAR_drive_poll_interval: ${{ vars.DRIVE_POLL_INTERVAL || '300' }}
  TF_VAR_function_url: ${{ vars.FUNCTION_URL || '' }}
```

## Terraform Variable Precedence

Terraform variables are loaded in this order (later overrides earlier):

1. **terraform.tfvars** - Local defaults
2. **TF_VAR_* environment variables** - GitHub Actions (highest priority)
3. **-var command line flags** - Not used in this workflow

This means:
- Local development uses `terraform.tfvars`
- CI/CD uses GitHub secrets/variables
- No need to modify `terraform.tfvars` for CI/CD

## Security Best Practices

### ✅ DO:
- Use Workload Identity Federation instead of service account keys
- Store sensitive values (tokens, project IDs, folder IDs) as **Secrets**
- Store non-sensitive values (intervals, repo names) as **Variables**
- Use environment-specific configurations with GitHub Environments
- Regularly rotate GitHub Personal Access Tokens

### ❌ DON'T:
- Commit `terraform.tfvars` with real values to git
- Share service account keys
- Use overly permissive IAM roles
- Store secrets in variables (they're visible in logs)

## Troubleshooting

### Error: "GCP_PROJECT_ID secret is not set"

**Solution**: Add the secret in GitHub Settings → Secrets and variables → Actions → Secrets

### Error: "could not find default credentials"

**Solutions**:
1. Verify `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_SERVICE_ACCOUNT` are set
2. Check that Workload Identity Federation is configured correctly
3. Verify the service account has `roles/iam.workloadIdentityUser` for GitHub

### Error: "Resource already exists"

**Solution**: The workflow automatically imports existing resources. This error should be transient.

### Terraform variables not being picked up

**Solution**:
1. Ensure secrets are named exactly as shown (case-sensitive)
2. Check that environment variables use `TF_VAR_` prefix
3. Verify workflow `env` section maps secrets correctly

## Example: Full Setup Checklist

- [ ] Create GCP project
- [ ] Enable billing on GCP project
- [ ] Create service account for Terraform
- [ ] Grant required IAM roles to service account
- [ ] Set up Workload Identity Federation
- [ ] Create GitHub Personal Access Token
- [ ] Add `GCP_PROJECT_ID` secret
- [ ] Add `GH_TOKEN` secret
- [ ] Add `GCP_WORKLOAD_IDENTITY_PROVIDER` secret
- [ ] Add `GCP_SERVICE_ACCOUNT` secret
- [ ] (Optional) Add `GOOGLE_DRIVE_FOLDER_ID` secret
- [ ] (Optional) Add `OBSIDIAN_DRIVE_FOLDER_ID` secret
- [ ] (Optional) Add `REPO_NAME` variable
- [ ] (Optional) Add `TERRAFORM_STATE_BUCKET` variable
- [ ] Test workflow with manual dispatch
- [ ] Verify function deployed successfully
- [ ] Update `FUNCTION_URL` variable with output

## Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Workload Identity Federation Setup](https://github.com/google-github-actions/auth#setting-up-workload-identity-federation)
- [Terraform Environment Variables](https://developer.hashicorp.com/terraform/cli/config/environment-variables)
- [GCP Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
