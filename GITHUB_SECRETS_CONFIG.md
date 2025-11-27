# GitHub Secrets Configuration Values

## ✅ GCP Infrastructure Setup Complete!

All service accounts and Workload Identity Federation have been created successfully.

---

## Configuration Values for GitHub Environments

### Environment 1: `terraform-plan` (Read-Only for PRs)

**Navigate to:** https://github.com/lordmuffin/maestro/settings/environments/new

**Environment name:** `terraform-plan`

**Protection rules:**
- ☐ Required reviewers: (none)
- ☐ Deployment branches: All branches

**Environment Secrets** (Click "Add secret"):

```
Name: GCP_WORKLOAD_IDENTITY_PROVIDER
Value: projects/116948413607/locations/global/workloadIdentityPools/github/providers/github-readonly
```

```
Name: GCP_SERVICE_ACCOUNT
Value: terraform-plan-readonly@gen-lang-client-0805519538.iam.gserviceaccount.com
```

**Environment Variables** (Click "Add variable"):

```
Name: TERRAFORM_STATE_BUCKET
Value: lordmuffin-maestro-tfstate
```

---

### Environment 2: `staging` (Auto-deploy from develop branch)

**Navigate to:** https://github.com/lordmuffin/maestro/settings/environments/new

**Environment name:** `staging`

**Protection rules:**
- ☐ Required reviewers: (none - auto-deploy)
- ☑ **Deployment branches:** Selected branches
  - Add branch: `develop`

**Environment Secrets** (Click "Add secret"):

```
Name: GCP_WORKLOAD_IDENTITY_PROVIDER
Value: projects/116948413607/locations/global/workloadIdentityPools/github/providers/github-staging
```

```
Name: GCP_SERVICE_ACCOUNT
Value: terraform-staging@gen-lang-client-0805519538.iam.gserviceaccount.com
```

```
Name: GCP_PROJECT_ID
Value: gen-lang-client-0805519538
```

**Copy these from your existing repository secrets:**

```
Name: TELEGRAM_BOT_TOKEN
Value: (copy from https://github.com/lordmuffin/maestro/settings/secrets/actions)
```

```
Name: GH_TOKEN_MAESTRO
Value: (copy from repository secrets)
```

```
Name: GH_TOKEN_BEYOND
Value: (copy from repository secrets)
```

```
Name: GOOGLE_DRIVE_FOLDER_ID
Value: (copy from repository secrets - if you have one)
```

```
Name: EMAIL_APP_PASSWORD
Value: (create at https://myaccount.google.com/apppasswords if not created)
```

**Environment Variables** (Click "Add variable"):

```
Name: TERRAFORM_STATE_BUCKET
Value: lordmuffin-maestro-tfstate
```

```
Name: NOTIFICATION_EMAIL
Value: dorkmeisterx69@gmail.com
```

```
Name: OBSIDIAN_DRIVE_FOLDER_ID
Value: (optional - copy from repository variables if you have one)
```

```
Name: KANBAN_FOLDER_ID
Value: (optional - copy from repository variables if you have one)
```

```
Name: DRIVE_POLL_INTERVAL
Value: 300
```

```
Name: FUNCTION_URL
Value: (leave empty for now - will be populated after first deployment)
```

---

### Environment 3: `production` (Manual approval required)

**Navigate to:** https://github.com/lordmuffin/maestro/settings/environments/new

**Environment name:** `production`

**Protection rules:**
- ☑ **Required reviewers:** 1
  - Select yourself: `lordmuffin`
- ☑ **Deployment branches:** Selected branches
  - Add branch: `main`

**Environment Secrets** (Click "Add secret"):

Copy ALL secrets from the existing `project-maestro-gcp` environment, OR use the same values as staging:

```
Name: GCP_WORKLOAD_IDENTITY_PROVIDER
Value: (use existing production WIF provider - check existing 'project-maestro-gcp' environment)
```

```
Name: GCP_SERVICE_ACCOUNT
Value: (use existing production SA - check existing 'project-maestro-gcp' environment)
```

```
Name: GCP_PROJECT_ID
Value: gen-lang-client-0805519538
```

```
Name: TELEGRAM_BOT_TOKEN
Value: (same as staging OR production bot token if different)
```

```
Name: GH_TOKEN_MAESTRO
Value: (same as staging)
```

```
Name: GH_TOKEN_BEYOND
Value: (same as staging)
```

```
Name: GOOGLE_DRIVE_FOLDER_ID
Value: (same as staging)
```

```
Name: EMAIL_APP_PASSWORD
Value: (same as staging)
```

**Environment Variables** (same as staging):

```
Name: TERRAFORM_STATE_BUCKET
Value: lordmuffin-maestro-tfstate
```

```
Name: NOTIFICATION_EMAIL
Value: dorkmeisterx69@gmail.com
```

```
Name: OBSIDIAN_DRIVE_FOLDER_ID
Value: (same as staging)
```

```
Name: KANBAN_FOLDER_ID
Value: (same as staging)
```

```
Name: DRIVE_POLL_INTERVAL
Value: 300
```

```
Name: FUNCTION_URL
Value: (leave empty)
```

---

## Quick Steps

1. **Check existing repository secrets:** https://github.com/lordmuffin/maestro/settings/secrets/actions
2. **Create terraform-plan environment** with secrets above
3. **Create staging environment** with secrets above
4. **Create production environment** with secrets above
5. **Re-run failed workflow:** https://github.com/lordmuffin/maestro/actions

---

## Verification

After creating all three environments, re-run the failed "Apply to Staging" workflow:

1. Go to: https://github.com/lordmuffin/maestro/actions
2. Find the failed workflow run
3. Click "Re-run all jobs"

Expected result: ✅ Authentication should succeed and staging deployment should proceed.

---

**Last Updated:** 2025-11-26
**Project:** gen-lang-client-0805519538 (Maestro)
**Project Number:** 116948413607
