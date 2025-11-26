# Multi-Repository Migration Guide

This guide documents the migration from single-repository to multi-repository support in Maestro.

## Overview

Maestro now supports multiple GitHub repositories with per-repository access tokens and context-based routing. This is a **breaking change** that requires full migration.

## Breaking Changes

### Removed Environment Variables
- `GITHUB_TOKEN` → Replaced with `GITHUB_TOKEN_MAESTRO`, `GITHUB_TOKEN_BEYOND`, etc.
- `REPO_NAME` → Configuration now in `repos.json`
- `BEYOND_REPO_NAME` → Configuration now in `repos.json`

### Updated Terraform Variables
- `github_token` → `github_tokens` (map)
- `repo_name` → Removed
- `beyond_repo_name` → Removed
- New: `repos_config_file` (default: `repos.json`)

## Migration Steps

### Step 1: Backup Current Configuration

```bash
# Backup Terraform variables
cp terraform/terraform.tfvars terraform/terraform.tfvars.backup

# Backup Terraform state
cd terraform
terraform state pull > terraform.tfstate.backup
```

### Step 2: Document Current Settings

```bash
# Record your current repository settings
echo "Current REPO_NAME: $REPO_NAME" >> migration-notes.txt
echo "Current BEYOND_REPO_NAME: $BEYOND_REPO_NAME" >> migration-notes.txt
```

### Step 3: Review Repository Configuration

The repository configuration is already created at `terraform/repos.json`. Review and update if needed:

```json
{
  "version": "1.0",
  "default_repository": "maestro",
  "repositories": [
    {
      "name": "lordmuffin/Maestro",
      "label": "maestro",
      "token_env_var": "GITHUB_TOKEN_MAESTRO",
      "description": "Main Maestro repository",
      "paths": {
        "sessions": "sessions/",
        "transcripts": "transcripts/"
      }
    },
    {
      "name": "lordmuffin/beyond",
      "label": "beyond",
      "token_env_var": "GITHUB_TOKEN_BEYOND",
      "description": "Beyond repository for interview notes",
      "paths": {
        "interviews": "05_Maestro_Notes/"
      }
    }
  ],
  "routing_rules": {
    "sessions": {"default_target": "maestro"},
    "transcripts": {"default_target": "maestro"},
    "interviews": {"default_target": "beyond"}
  }
}
```

**Customization**: Update repository names, labels, and paths as needed for your setup.

### Step 4: Update GitHub Actions Secrets (if using CI/CD)

If you're using GitHub Actions for deployment:

1. Go to your repository: `Settings` → `Secrets and variables` → `Actions` → `Repository secrets`

2. **Add new secrets**:
   - `GH_TOKEN_MAESTRO` - Your GitHub token for Maestro repository
   - `GH_TOKEN_BEYOND` - Your GitHub token for Beyond repository

   Note: You can use the same token value for both if they're accessible with the same account.

3. **Remove old variables** (if they exist):
   - Go to `Variables` tab
   - Delete `REPO_NAME`
   - Delete `BEYOND_REPO_NAME`

The workflow file (`.github/workflows/terraform.yml`) has already been updated to use the new secrets.

### Step 5: Update Terraform Variables

Edit `terraform/terraform.tfvars` and replace the GitHub section:

**BEFORE**:
```hcl
github_token = "ghp_xxx"
repo_name    = "lordmuffin/Maestro"
beyond_repo_name = "lordmuffin/beyond"
```

**AFTER**:
```hcl
github_tokens = {
  maestro = "ghp_xxx"  # Can reuse same token
  beyond  = "ghp_xxx"  # Can reuse same token
}
repos_config_file = "repos.json"
```

**Note**: You can use the same token value for multiple repositories if they're all accessible with the same GitHub account.

### Step 6: Review Terraform Plan

```bash
cd terraform
terraform plan
```

Expected changes:
- Environment variables updated (removal of old vars, addition of new token vars)
- Cloud Function redeployment triggered (due to code and config changes)

### Step 7: Apply Terraform Changes

```bash
terraform apply
```

Confirm the changes when prompted.

### Step 8: Verify Deployment

Check the Cloud Function logs to confirm successful configuration loading:

```bash
gcloud functions logs read v2v2b-interrogator \
  --region=us-central1 \
  --limit=50 | grep -i "repository\|config"
```

Expected log entries:
```
Loaded configuration from repos.json
Configured repositories: ['maestro', 'beyond']
GitHubManager initialized with multi-repo support
All repository tokens are configured
```

### Step 9: Test Health Check Endpoint

```bash
curl https://YOUR-FUNCTION-URL/health/repos
# or
curl https://YOUR-FUNCTION-URL?mode=health_repos
```

Expected response:
```json
{
  "status": "healthy",
  "config_version": "1.0",
  "default_repository": "maestro",
  "repositories": [
    {
      "label": "maestro",
      "name": "lordmuffin/Maestro",
      "token_env_var": "GITHUB_TOKEN_MAESTRO",
      "token_available": true,
      "accessible": true,
      "error": null
    },
    {
      "label": "beyond",
      "name": "lordmuffin/beyond",
      "token_env_var": "GITHUB_TOKEN_BEYOND",
      "token_available": true,
      "accessible": true,
      "error": null
    }
  ]
}
```

### Step 10: Test PR Creation

1. **Test Session PR** (Telegram):
   - Send `/done` command
   - Verify PR created in Maestro repository
   - Check file path is `sessions/YYYY-MM-DD-*.md`

2. **Test Interview PR** (Telegram):
   - Complete an interview
   - Verify PR created in Beyond repository
   - Check file path is `05_Maestro_Notes/YYYY-MM-DD - *.md`

3. **Test Transcript PR** (Google Drive):
   - Upload transcript file to monitored folder
   - Verify PR created in Maestro repository
   - Check file path is `transcripts/YYYY-MM-DD-*.md`

## Rollback Procedures

If issues occur during migration:

### Quick Rollback

```bash
cd terraform

# Option 1: Restore from backup
terraform apply -var-file=terraform.tfvars.backup

# Option 2: Git revert
git revert HEAD
terraform apply
```

### Manual Fix

If Terraform rollback fails, manually update environment variables in GCP Console:

1. Go to Cloud Functions → v2v2b-interrogator → Edit
2. Add environment variables:
   - `GITHUB_TOKEN` = your token
   - `REPO_NAME` = `lordmuffin/Maestro`
   - `BEYOND_REPO_NAME` = `lordmuffin/beyond`
3. Deploy

## New Features

### Repository Health Check

Check repository configuration and accessibility:
```bash
curl https://YOUR-FUNCTION-URL/health/repos
```

### Configurable File Paths

File paths are now configurable per repository in `repos.json`:

```json
{
  "repositories": [
    {
      "name": "user/repo",
      "paths": {
        "sessions": "custom/sessions/",
        "transcripts": "custom/transcripts/",
        "interviews": "custom/interviews/"
      }
    }
  ]
}
```

### Context-Based Routing

PRs are automatically routed to appropriate repositories:
- **Sessions** → maestro repository
- **Transcripts** → maestro repository
- **Interviews** → beyond repository

Override routing by specifying `repo_label` in code.

## Troubleshooting

### Issue: "Configuration file not found"

**Cause**: `repos.json` not included in deployment package

**Solution**:
1. Verify `terraform/repos.json` exists
2. Check `terraform/main.tf` includes the repos.json source
3. Run `terraform apply` to redeploy

### Issue: "Token not found for GITHUB_TOKEN_MAESTRO"

**Cause**: Environment variable not set

**Solution**:
1. Update `terraform.tfvars` with `github_tokens` map
2. Run `terraform apply`
3. Verify with health check endpoint

### Issue: "Repository not accessible"

**Cause**: Invalid token or insufficient permissions

**Solution**:
1. Verify token has write access to repository
2. Check token hasn't expired
3. Ensure token has repo scope
4. Test with health check endpoint

### Issue: PRs created in wrong repository

**Cause**: Routing rules not configured correctly

**Solution**:
1. Check `routing_rules` in `repos.json`
2. Verify `default_target` matches repository label
3. Update configuration and redeploy

## Configuration Examples

### Single Token for Multiple Repos

```hcl
# terraform.tfvars
github_tokens = {
  maestro = "ghp_same_token"
  beyond  = "ghp_same_token"
  notes   = "ghp_same_token"
}
```

### Different Tokens Per Repo

```hcl
# terraform.tfvars
github_tokens = {
  work    = "ghp_work_token"
  personal = "ghp_personal_token"
}
```

### Adding a New Repository

1. Edit `terraform/repos.json`:
```json
{
  "repositories": [
    ...existing repos...,
    {
      "name": "user/new-repo",
      "label": "newrepo",
      "token_env_var": "GITHUB_TOKEN_NEWREPO",
      "description": "New repository",
      "paths": {
        "sessions": "sessions/"
      }
    }
  ]
}
```

2. Update `terraform/terraform.tfvars`:
```hcl
github_tokens = {
  maestro = "ghp_xxx"
  beyond  = "ghp_xxx"
  newrepo = "ghp_xxx"  # Add new token
}
```

3. Deploy:
```bash
terraform apply
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/lordmuffin/Maestro/issues
- Review plan: `.claude/plans/rippling-mixing-lemur.md`

## Migration Checklist

- [ ] Backup terraform.tfvars
- [ ] Backup Terraform state
- [ ] Document current REPO_NAME and BEYOND_REPO_NAME
- [ ] Review and customize repos.json
- [ ] Update terraform.tfvars with github_tokens
- [ ] Run terraform plan
- [ ] Run terraform apply
- [ ] Check Cloud Function logs
- [ ] Test health check endpoint (returns 200)
- [ ] Test session PR creation
- [ ] Test interview PR creation
- [ ] Test transcript PR creation
- [ ] Verify file paths in PRs
- [ ] Monitor for errors in production
