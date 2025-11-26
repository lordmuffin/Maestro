# Terraform Workflow Migration Guide

## ⚠️ IMPORTANT: Workflow Changes (Phase 1 - GitOps HITL Implementation)

The Terraform workflows have been refactored to implement secure GitOps practices with Human-in-the-Loop (HITL) governance gates.

## What Changed?

### Disabled Workflows

#### `terraform.yml` → `terraform.yml.disabled`
**Reason**: This workflow contained insecure automatic deployment mechanisms.

**Issues with old workflow**:
- ❌ Automatic `terraform apply` on push to main (lines 209-214)
- ❌ Manual `terraform destroy` capability (lines 216-218)
- ❌ Pointed to old directory structure (`./terraform`)
- ❌ Bypassed human review for infrastructure changes
- ❌ GCP authentication not properly configured

#### `terraform-apply-template.yml` → **REMOVED**
**Reason**: Reusable workflow with extensive `terraform apply` logic that bypassed HITL governance.

### New Workflows

#### ✅ `terraform-pr-pipeline.yml` (Active - Phase 1)
**Purpose**: Secure plan-only workflow that enforces HITL governance.

**Features**:
- ✅ Only runs `terraform plan` (NO apply/destroy)
- ✅ Automatically creates/updates Pull Requests
- ✅ Includes Terraform plan output in PR body
- ✅ Runs security scanning (tfsec)
- ✅ Works with new directory: `iac/maestro-artifacts/terraform/`
- ✅ Requires explicit PR approval before any deployment
- ✅ Comprehensive validation and formatting checks

**Triggers**:
- Push to non-main branches affecting `iac/maestro-artifacts/terraform/**`
- Manual workflow dispatch

## Current Deployment Process (Phase 1)

### For Infrastructure Changes:

1. **Make Changes**: Modify files in `iac/maestro-artifacts/terraform/`
2. **Commit & Push**: Push to a feature branch (not main)
3. **Automatic PR**: Workflow creates PR with Terraform plan
4. **Human Review**: DevOps team reviews the proposed changes
5. **Approval**: PR must be approved by authorized reviewers
6. **Merge**: Merge PR to main
7. **Manual Deploy**: (Temporary) Manual deployment required until Phase 2

### Emergency Procedures:

If urgent deployment is needed:
1. Re-enable `terraform.yml.disabled` temporarily by renaming to `terraform.yml`
2. Update the `WORKING_DIR` to `iac/maestro-artifacts/terraform`
3. Use `workflow_dispatch` with `action: apply`
4. **IMMEDIATELY** disable the workflow again after deployment
5. Document the emergency deployment in an incident report

## Future: Phase 2 Implementation

Phase 2 will add automated deployment with additional safeguards:

### Planned Features:
- **Policy-as-Code**: OPA/Rego validation before plan approval
- **Automated Deployment**: Auto-apply after PR merge to main
- **Cost Guardrails**: Automatic cost estimation and thresholds
- **Compliance Checks**: Automated policy validation
- **Rollback Mechanism**: Automatic rollback on deployment failure
- **Audit Logging**: Enhanced deployment audit trails

### Phase 2 Workflow:
1. Push changes → `terraform-pr-pipeline.yml` creates PR
2. Review & approve PR
3. Merge to main → **NEW** `terraform-deploy.yml` auto-applies
4. Deployment monitored with automatic rollback
5. Full audit trail maintained

## Directory Structure Migration

### Old Structure (Deprecated):
```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
└── ...
```

### New Structure (Active):
```
iac/maestro-artifacts/
├── README.md                    # Artifact contract documentation
└── terraform/
    ├── main.tf                  # All Terraform files moved here
    ├── variables.tf
    ├── outputs.tf
    ├── backend.tf
    └── ...
```

## Troubleshooting

### "Terraform directory not found" errors
**Solution**: Update workflow to use `iac/maestro-artifacts/terraform/` instead of `./terraform`

### "GCP authentication failed" errors
**Solution**: Ensure `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_SERVICE_ACCOUNT` secrets are configured, OR use `GCP_CREDENTIALS` secret with service account JSON

### "Workflow not triggering" issues
**Solution**: Ensure changes are in `iac/maestro-artifacts/terraform/**` path and pushed to a non-main branch

### "No PR created" issues
**Solution**: Check that you're not pushing to main/master branch directly

## Security Benefits

✅ **No Automatic Deployment**: All changes require explicit approval
✅ **Security Scanning**: tfsec runs on every plan
✅ **Audit Trail**: Git history tracks all infrastructure changes
✅ **Review Process**: Mandatory PR review before deployment
✅ **Validation**: Terraform validate, fmt, and init checks

## Questions?

- **Documentation**: See `iac/maestro-artifacts/README.md`
- **Issues**: Open an issue with the `gitops` label
- **Emergency**: Contact DevOps team lead

---

**Last Updated**: 2025-11-26
**Phase**: 1 (Plan & Review)
**Status**: Active
