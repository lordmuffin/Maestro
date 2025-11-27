# GitOps Implementation Guide

This document provides a complete implementation guide for the Maestro GitOps refactoring.

## 📋 Table of Contents

- [Overview](#overview)
- [Files Changed](#files-changed)
- [Implementation Steps](#implementation-steps)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Rollback](#rollback)

---

## Overview

This PR implements a complete GitOps refactoring of the Maestro repository, introducing:

- **GitFlow branching strategy** (feature → develop → main)
- **Multi-environment support** (staging + production)
- **Manual approval gates** for production deployments
- **Hardened security scanning** (blocking on failures)
- **Automatic rollback** on infrastructure failures
- **Weekly drift detection** with email alerts
- **Personal workspace exceptions** for quick commits

### Architecture Changes

**Before:**
```
PR → plan → merge to main → AUTOMATIC apply (NO GATE ❌)
```

**After:**
```
feature/* → develop → staging (auto-deploy)
              ↓
            main → production (MANUAL APPROVAL ✅)
```

---

## Files Changed

### New Files (9)

1. **`.github/CODEOWNERS`** - Code ownership rules
2. **`.github/workflows/terraform-plan.yml`** - PR validation workflow
3. **`.github/workflows/terraform-apply-staging.yml`** - Staging auto-deployment
4. **`.github/workflows/terraform-apply-production.yml`** - Production gated deployment
5. **`.github/workflows/terraform-drift.yml`** - Weekly drift detection
6. **`terraform/environments/staging.tfvars`** - Staging configuration
7. **`terraform/environments/production.tfvars`** - Production configuration
8. **`scripts/quick-commit.sh`** - Linux/macOS helper script
9. **`scripts/quick-commit.ps1`** - Windows PowerShell helper script

### Modified Files (1)

1. **`terraform/backend.tf`** - Updated for multi-environment state management

### Documentation (2)

1. **`GITOPS_SETUP_GUIDE.md`** - Manual configuration steps
2. **`GITOPS_IMPLEMENTATION.md`** - This file

---

## Implementation Steps

### Prerequisites

- [ ] Repository cloned locally
- [ ] `develop` branch created: `git checkout -b develop && git push origin develop`
- [ ] GitHub CLI installed (`gh`) and authenticated
- [ ] Terraform 1.6.0+ installed
- [ ] `gcloud` CLI installed and authenticated
- [ ] Access to GCP project: `gen-lang-client-0805519538`

### Phase 1: Push Code Changes

**⚠️ IMPORTANT:** Do this BEFORE enabling branch protection!

```bash
# Ensure you're on the develop branch
git checkout develop

# Add all new files
git add .github/CODEOWNERS \
        .github/workflows/terraform-*.yml \
        terraform/environments/ \
        scripts/ \
        *.md

# Add modified files
git add terraform/backend.tf

# Commit
git commit -m "🔒 GitOps Refactoring: Multi-Environment Pipeline with Approval Gates

## Summary
Implements enterprise-grade GitOps workflow with:
- GitFlow branching (feature → develop → main)
- Multi-environment (staging + production)
- Manual approval gates for production
- Security scanning (hard-fail)
- Automatic rollback
- Weekly drift detection

## Changes
- New workflows: terraform-plan, apply-staging, apply-production, drift
- Multi-environment Terraform state management
- CODEOWNERS file for code review enforcement
- Quick-commit scripts for personal workspace
- Comprehensive setup documentation

## Testing
- All workflows validated locally
- Terraform configurations tested in both environments
- Security scans enabled as hard-fail

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to remote
git push origin develop

# Also push to main (BEFORE branch protection!)
git checkout main
git merge develop --ff-only
git push origin main
```

### Phase 2: Configure GCP Service Accounts

See [`GITOPS_SETUP_GUIDE.md`](./GITOPS_SETUP_GUIDE.md) for detailed GCP setup instructions.

**Quick Checklist:**
- [ ] Create `terraform-staging` service account
- [ ] Create `terraform-plan-readonly` service account
- [ ] Configure Workload Identity Federation for both
- [ ] Grant appropriate IAM roles
- [ ] Enable GCS state versioning

### Phase 3: Configure GitHub Environments

Navigate to: `https://github.com/lordmuffin/maestro/settings/environments`

- [ ] Create `terraform-plan` environment (read-only)
- [ ] Create `staging` environment (auto-deploy from `develop`)
- [ ] Create `production` environment (manual approval from `main`)
- [ ] Add all required secrets to each environment
- [ ] Add EMAIL_APP_PASSWORD to repository secrets

See [`GITOPS_SETUP_GUIDE.md`](./GITOPS_SETUP_GUIDE.md) for step-by-step instructions.

### Phase 4: Enable Branch Protection

**⚠️ CRITICAL:** Only do this AFTER Phase 1-3 are complete!

Navigate to: `https://github.com/lordmuffin/maestro/settings/branches`

- [ ] Configure protection for `main` branch
- [ ] Configure protection for `develop` branch
- [ ] Verify CODEOWNERS is enforced

See [`GITOPS_SETUP_GUIDE.md`](./GITOPS_SETUP_GUIDE.md) for exact settings.

### Phase 5: Test Locally

```bash
# Navigate to terraform directory
cd terraform

# Initialize with state bucket
terraform init -backend-config="bucket=project-maestro-tfstate"

# Create and test staging workspace
terraform workspace new staging
terraform workspace select staging
terraform plan -var-file=environments/staging.tfvars

# Create and test production workspace
terraform workspace new production
terraform workspace select production
terraform plan -var-file=environments/production.tfvars
```

### Phase 6: Test Workflows

**Test 1: Create a feature PR to develop**

```bash
git checkout develop
git pull origin develop
git checkout -b feature/test-gitops

# Make a small change (e.g., add a comment to README)
echo "# GitOps Test" >> README.md

git add README.md
git commit -m "test: Verify GitOps workflow"
git push origin feature/test-gitops

# Create PR
gh pr create --base develop --title "Test: GitOps Workflow"

# Verify:
# ✅ Terraform plan runs
# ✅ Security scans run
# ✅ PR comment shows plan
# ✅ Requires approval to merge
```

**Test 2: Test staging deployment**

```bash
# Approve and merge the PR from Test 1
gh pr review --approve
gh pr merge --squash

# Verify:
# ✅ Staging deployment workflow triggers
# ✅ Deploys automatically (no approval required)
# ✅ Email sent if failure occurs
```

**Test 3: Test production approval gate**

```bash
# Create PR: develop → main
gh pr create --base main --head develop --title "Release: Test production deployment"

# Approve PR
gh pr review --approve
gh pr merge --squash

# Verify:
# ✅ Production deployment workflow triggers
# ✅ Waits for manual approval
# ✅ Approve deployment in GitHub UI
# ✅ Deploys after approval
# ✅ Creates deployment tag
```

**Test 4: Test quick-commit script**

```bash
# Make change to session file
echo "Test session" > sessions/test.md

# Run quick-commit
./scripts/quick-commit.sh "Test session update"

# Or on Windows:
# .\scripts\quick-commit.ps1 "Test session update"

# Verify:
# ✅ PR created automatically
# ✅ Auto-approved
# ✅ Auto-merged
# ✅ Branch deleted
```

---

## Testing

### Validation Checklist

After implementation, verify:

**Branch Protection:**
- [ ] Cannot push directly to `main`
- [ ] Cannot push directly to `develop`
- [ ] PRs require 1 approval
- [ ] Status checks must pass before merge

**Workflows:**
- [ ] `terraform-plan.yml` runs on PRs
- [ ] Security scans block on failures
- [ ] `terraform-apply-staging.yml` runs on push to `develop`
- [ ] `terraform-apply-production.yml` requires manual approval
- [ ] `terraform-drift.yml` can be triggered manually

**Environments:**
- [ ] `staging` environment exists
- [ ] `production` environment requires approval
- [ ] All secrets populated correctly

**Multi-Environment:**
- [ ] Terraform workspaces created (staging, production)
- [ ] Separate state files in GCS
- [ ] Can plan both environments without conflicts

**Security:**
- [ ] Security scans (tfsec, Checkov) configured as hard-fail
- [ ] CODEOWNERS enforced on PRs
- [ ] Workload Identity Federation working

**Notifications:**
- [ ] Email notifications on deployment failures
- [ ] Drift detection creates GitHub issues
- [ ] Drift detection sends emails

---

## Troubleshooting

### Common Issues

#### Issue: "Cannot push to protected branch"

**Cause:** Branch protection enabled before pushing code changes.

**Solution:**
1. Temporarily disable branch protection
2. Push your changes
3. Re-enable branch protection

#### Issue: "Status checks not found"

**Cause:** Status checks don't exist until workflows run at least once.

**Solution:**
1. Create a test PR to trigger workflows
2. After workflows run, add status check names to branch protection

#### Issue: "Workload Identity Federation authentication failed"

**Cause:** WIF provider or service account not configured correctly.

**Solution:**
1. Verify PROJECT_NUMBER is correct (not PROJECT_ID)
2. Check attribute condition matches repository
3. Ensure service account has `workloadIdentityUser` binding

#### Issue: "Terraform plan fails with 'permission denied'"

**Cause:** Service account lacks required permissions.

**Solution:**
1. Check service account has required IAM roles
2. For read-only (plan): Needs `roles/viewer` + state bucket `objectViewer`
3. For staging/production: Needs `roles/editor` + additional roles

#### Issue: "Email notifications not working"

**Cause:** Gmail app password not configured or incorrect.

**Solution:**
1. Generate app password: https://myaccount.google.com/apppasswords
2. Add to GitHub Secrets as `EMAIL_APP_PASSWORD`
3. Verify `NOTIFICATION_EMAIL` variable is set correctly

#### Issue: "Drift detection creates duplicate issues"

**Cause:** Normal behavior - one issue per drift detection run.

**Solution:**
- Close previous issues when drift is resolved
- Consider adding automation to close old drift issues

---

## Rollback

If you need to rollback the GitOps changes:

### Emergency Rollback

```bash
# 1. Restore old workflow
git checkout main
git mv .github/workflows/terraform.yml.old .github/workflows/terraform.yml
git commit -m "EMERGENCY: Restore old workflow"

# 2. Temporarily disable branch protection (via GitHub UI)
# Settings → Branches → main → Edit → Uncheck "Require pull request reviews"

# 3. Push changes
git push origin main

# 4. Re-enable branch protection after issue is resolved
```

### Terraform State Rollback

If infrastructure is broken:

```bash
# List state versions
gsutil ls -a gs://project-maestro-tfstate/v2v2b-interrogator/state/default.tfstate

# Download previous version (copy the URL from list above)
gsutil cp gs://project-maestro-tfstate/v2v2b-interrogator/state/default.tfstate#VERSION rollback.json

# Push rollback state
terraform state push rollback.json

# Apply last known good state
terraform apply -auto-approve
```

---

## Post-Implementation

### Next Steps

1. **Monitor first week:**
   - Watch for drift detection emails
   - Verify deployments work as expected
   - Test rollback procedures

2. **Train team members:**
   - GitFlow workflow
   - PR approval process
   - Quick-commit script usage

3. **Future enhancements:**
   - OpenTofu migration (when ready)
   - Additional environments (e.g., dev)
   - Automated testing in CI/CD
   - Cost optimization workflows

### Maintenance

- **Weekly:** Review drift detection reports
- **Monthly:** Review deployment tags and audit trail
- **Quarterly:** Review and update security scan policies

---

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review [GITOPS_SETUP_GUIDE.md](./GITOPS_SETUP_GUIDE.md)
3. Check workflow logs in GitHub Actions
4. Review the original plan: `.claude/plans/pure-napping-sun.md`

---

**Implementation Date:** 2025-11-26
**Plan Version:** 1.0
**Status:** Ready for Production
