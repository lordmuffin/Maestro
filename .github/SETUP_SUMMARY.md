# Setup Summary - Centralized Configuration

## What Changed

The Terraform deployment workflow has been updated to use **centralized environment variables** from GitHub secrets and variables. This means all configuration is now stored in one location instead of being scattered across multiple files.

## Before vs After

### Before ❌
- Hardcoded defaults in workflow file
- Variables passed inline with `-var` flags
- Configuration duplicated in import commands
- Difficult to update values

### After ✅
- All variables defined in `env:` section
- Terraform automatically picks up `TF_VAR_*` variables
- Single source of truth for configuration
- Easy to update via GitHub UI

## Files Modified

1. **`.github/workflows/terraform.yml`**
   - Added centralized `env:` section with `TF_VAR_*` variables
   - Simplified import commands (no inline variables)
   - Simplified plan/apply/destroy commands
   - Added configuration validation step

2. **`terraform/terraform.tfvars`**
   - Created with default values for local development
   - GitHub Actions overrides these with secrets

3. **`.github/CONFIGURATION.md`** (NEW)
   - Complete guide for setting up GitHub secrets
   - Step-by-step instructions
   - Security best practices

4. **`terraform/README.md`**
   - Added reference to configuration guide
   - Updated CI/CD section with workflow features

## Required GitHub Secrets

You need to configure these in: **Settings → Secrets and variables → Actions → Secrets**

### Required:
- `GCP_PROJECT_ID` - Your GCP project ID
- `GH_TOKEN` - GitHub Personal Access Token
- `GCP_WORKLOAD_IDENTITY_PROVIDER` - Workload Identity provider string
- `GCP_SERVICE_ACCOUNT` - Service account email

### Optional (Google Drive):
- `GOOGLE_DRIVE_FOLDER_ID` - Folder ID for transcript monitoring
- `OBSIDIAN_DRIVE_FOLDER_ID` - Folder ID for Obsidian vault

## Quick Setup Steps

1. **Add Required Secrets** (see [CONFIGURATION.md](CONFIGURATION.md) for details):
   ```
   Settings → Secrets and variables → Actions → New repository secret
   ```

2. **Verify Configuration** by running the workflow:
   ```
   Actions → Terraform Deploy → Run workflow
   ```

3. **Check Validation Output**:
   The workflow now validates all configuration and shows:
   - ✅ Project ID
   - ✅ Repository name
   - ✅ Drive folder status
   - ✅ Poll interval

## How It Works

### Centralized Environment Variables

All Terraform variables are defined once in the workflow `env:` section:

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

### Automatic Variable Injection

Terraform automatically picks up any environment variable starting with `TF_VAR_`:

```bash
# No need for -var flags anymore!
terraform plan   # ✅ Uses TF_VAR_* from environment
terraform apply  # ✅ Uses TF_VAR_* from environment
```

### Simplified Commands

**Before:**
```bash
terraform plan \
  -var="gcp_project=${{ secrets.GCP_PROJECT_ID }}" \
  -var="github_token=${{ secrets.GH_TOKEN }}" \
  -var="repo_name=${{ secrets.REPO_NAME }}"
```

**After:**
```bash
terraform plan  # All variables already in environment
```

## Benefits

1. **Single Source of Truth** - All config in GitHub UI
2. **Easier Updates** - Change secrets/variables in one place
3. **Less Duplication** - Variables defined once
4. **Better Security** - Secrets not exposed in workflow logs
5. **Simpler Commands** - No inline variable passing
6. **Validation** - Automatic check before deployment

## Migration Checklist

If you're updating from the old workflow:

- [ ] Add `GCP_PROJECT_ID` secret
- [ ] Add `GH_TOKEN` secret
- [ ] Add `GCP_WORKLOAD_IDENTITY_PROVIDER` secret
- [ ] Add `GCP_SERVICE_ACCOUNT` secret
- [ ] (Optional) Add `GOOGLE_DRIVE_FOLDER_ID` secret
- [ ] (Optional) Add `OBSIDIAN_DRIVE_FOLDER_ID` secret
- [ ] Test workflow with manual dispatch
- [ ] Verify validation step passes
- [ ] Confirm deployment succeeds

## Troubleshooting

### "GCP_PROJECT_ID secret is not set"
**Fix**: Add the secret in GitHub Settings → Secrets → GCP_PROJECT_ID

### "could not find default credentials"
**Fix**: Verify Workload Identity secrets are configured correctly

### Variables not being used
**Fix**: Ensure secret names match exactly (case-sensitive)

## Next Steps

1. Review [CONFIGURATION.md](CONFIGURATION.md) for detailed setup instructions
2. Add required GitHub secrets
3. Test deployment with workflow dispatch
4. Monitor workflow output for validation confirmation

## Support

For issues or questions:
- See [CONFIGURATION.md](CONFIGURATION.md) for setup details
- Check [terraform/README.md](../terraform/README.md) for Terraform documentation
- Review workflow logs for specific error messages
