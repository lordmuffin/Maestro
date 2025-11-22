# GitHub Actions Terraform Setup Guide

This guide will help you set up the required secrets and permissions for the Terraform GitHub Actions workflow.

## Required GitHub Secrets

Navigate to your repository's **Settings > Secrets and variables > Actions** and add the following secrets:

### 1. GCP Authentication

Choose **ONE** of the following authentication methods:

#### Option A: Service Account Key (Simpler, Less Secure)

1. Create a service account in GCP:
```bash
gcloud iam service-accounts create github-actions-terraform \
  --display-name="GitHub Actions Terraform"
```

2. Grant necessary permissions:
```bash
PROJECT_ID="your-project-id"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudfunctions.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor"
```

3. Create and download the key:
```bash
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com
```

4. Add to GitHub Secrets:
   - Secret name: `GCP_CREDENTIALS`
   - Secret value: Contents of `github-actions-key.json`

5. **Important**: Delete the local key file after uploading:
```bash
rm github-actions-key.json
```

#### Option B: Workload Identity Federation (Recommended for Production)

1. Create a Workload Identity Pool:
```bash
PROJECT_ID="your-project-id"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud iam workload-identity-pools create "github-actions" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions"
```

2. Create a Workload Identity Provider:
```bash
REPO_OWNER="your-github-username"
REPO_NAME="your-repo-name"

gcloud iam workload-identity-pools providers create-oidc "github" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

3. Create a service account:
```bash
gcloud iam service-accounts create github-actions-terraform \
  --display-name="GitHub Actions Terraform"
```

4. Grant permissions (same as Option A above)

5. Allow GitHub Actions to impersonate the service account:
```bash
gcloud iam service-accounts add-iam-policy-binding \
  "github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository/${REPO_OWNER}/${REPO_NAME}"
```

6. Add to GitHub Secrets:
   - Secret name: `GCP_WORKLOAD_IDENTITY_PROVIDER`
   - Secret value: `projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/providers/github`

   - Secret name: `GCP_SERVICE_ACCOUNT`
   - Secret value: `github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com`

7. Update `.github/workflows/terraform.yml`:
   - Comment out the "Service Account Key" section
   - Uncomment the "Workload Identity" section

### 2. GCP Project Configuration

- **Secret name**: `GCP_PROJECT_ID`
- **Secret value**: Your GCP project ID (e.g., `my-project-12345`)

### 3. GitHub Token

- **Secret name**: `GH_TOKEN`
- **Secret value**: Your GitHub Personal Access Token

  To create a token:
  1. Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
  2. Generate new token with `repo` scope
  3. Copy the token value

### 4. Repository Name

- **Secret name**: `REPO_NAME`
- **Secret value**: Your repository in format `username/repo` (e.g., `lordmuffin/Maestro`)

## Workflow Features

### Automatic Triggers

1. **Pull Requests**: Runs `terraform plan` and comments the plan on the PR
2. **Push to Main**: Runs `terraform apply` automatically
3. **Manual Trigger**: Use "Run workflow" button with options for plan/apply/destroy

### Security Scanning

The workflow includes two security scanners that run on PRs:
- **tfsec**: Scans for security issues in Terraform code
- **Checkov**: Validates infrastructure-as-code security and compliance

### Workflow Outputs

After successful deployment, the workflow will display:
- Function Name
- Function URL
- Full deployment summary

## Testing the Workflow

### Test Plan (Manual Run)

1. Go to Actions tab in GitHub
2. Select "Terraform Deploy" workflow
3. Click "Run workflow"
4. Select "plan" action
5. Verify the plan completes successfully

### Test Apply (Push to Main)

1. Make a small change to terraform files
2. Create a PR
3. Verify plan runs and comments on PR
4. Merge PR to main
5. Verify apply runs automatically

## Troubleshooting

### Authentication Errors

```
Error: google: could not find default credentials
```

**Solution**: Ensure `GCP_CREDENTIALS` secret is set correctly with valid JSON

### Permission Denied Errors

```
Error: Error creating function: googleapi: Error 403: Permission denied
```

**Solution**: Verify the service account has all required roles (see setup above)

### Missing Secrets

```
Error: Required variable not set: gcp_project
```

**Solution**: Ensure all required secrets are configured in GitHub

### State Lock Errors

If using GCS backend and getting lock errors:

```bash
# Manually unlock (use with caution)
terraform force-unlock <lock-id>
```

## Backend Configuration

If using a remote backend (GCS or Terraform Cloud), update the workflow to include:

```yaml
- name: Terraform Init
  run: |
    terraform init \
      -backend-config="bucket=${{ secrets.TF_STATE_BUCKET }}" \
      -backend-config="prefix=v2v2b-interrogator/state"
```

And add the secret:
- **Secret name**: `TF_STATE_BUCKET`
- **Secret value**: Your GCS bucket name

## Cost Optimization

To avoid unnecessary runs:

1. The workflow only triggers on changes to `terraform/**` files
2. PRs only run `plan` (no cost)
3. Only pushes to `main` run `apply`
4. Manual triggers require explicit confirmation

## Security Best Practices

1. ✅ Use Workload Identity Federation instead of service account keys
2. ✅ Never commit credentials to the repository
3. ✅ Use separate service accounts for different environments
4. ✅ Enable branch protection on `main` to require PR reviews
5. ✅ Regularly rotate service account keys (if using them)
6. ✅ Review security scan results before merging PRs
7. ✅ Use least-privilege IAM roles

## Additional Configuration

### Environment-Specific Deployments

To deploy to multiple environments (dev, staging, prod):

1. Create separate workflows or use environments:
```yaml
environment:
  name: production
  url: ${{ steps.outputs.outputs.function_url }}
```

2. Use environment-specific secrets in GitHub

### Notifications

Add Slack or email notifications on failure:

```yaml
- name: Notify on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
```

## Support

For issues with:
- **GitHub Actions**: Check the Actions tab for detailed logs
- **Terraform**: Review terraform plan output in PR comments
- **GCP**: Check Google Cloud Console for resource status
