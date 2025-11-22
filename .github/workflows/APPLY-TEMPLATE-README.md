# Terraform Apply Pipeline Template

A comprehensive, production-ready Terraform apply pipeline with enhanced safety features, multi-environment support, and automated rollback capabilities.

## 🚀 Features

### Core Features
- **Multi-environment support** (dev, staging, production)
- **Manual approval gates** for production deployments
- **Automated rollback** on deployment failures
- **Drift detection** before apply
- **Cost estimation** and threshold checking
- **Comprehensive security scanning**
- **State backup and restoration**
- **Real-time notifications** (Slack, GitHub)

### Safety Features
- **Pre-deployment validation**
- **Resource tagging** automation
- **Health check testing**
- **Configuration format checking**
- **Security compliance scanning**
- **Deployment summaries**

## 📋 Prerequisites

### Required GitHub Secrets
Configure these in your repository or environment settings:

#### Authentication (choose one)
**Option A: Workload Identity Federation (Recommended)**
```
GCP_WORKLOAD_IDENTITY_PROVIDER  # projects/123/locations/global/workloadIdentityPools/pool/providers/provider
GCP_SERVICE_ACCOUNT             # service-account@project.iam.gserviceaccount.com
```

**Option B: Service Account Key**
```
GCP_CREDENTIALS                 # JSON key content
```

#### Required Secrets
```
GH_TOKEN                        # GitHub Personal Access Token
```

#### Optional Notification Secrets
```
SLACK_WEBHOOK                   # Slack webhook URL
NOTIFICATION_EMAIL              # Email for notifications
```

### Required GitHub Variables
```
GCP_PROJECT_ID                  # Your GCP project ID
REPO_NAME                       # Repository name (owner/repo)
```

## 🔧 Usage

### As a Reusable Workflow

Create a workflow file in your repository (e.g., `.github/workflows/deploy-production.yml`):

```yaml
name: Deploy to Production

on:
  workflow_dispatch:
    inputs:
      confirm_production:
        description: 'Type "CONFIRM" to deploy to production'
        required: true
        type: string

jobs:
  deploy:
    if: github.event.inputs.confirm_production == 'CONFIRM'
    uses: ./.github/workflows/terraform-apply-template.yml
    with:
      environment: 'production'
      auto_approve: false
      cost_threshold: 500
      enable_notifications: true
    secrets:
      GCP_WORKLOAD_IDENTITY_PROVIDER: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
      GCP_SERVICE_ACCOUNT: ${{ secrets.GCP_SERVICE_ACCOUNT }}
      GH_TOKEN: ${{ secrets.GH_TOKEN }}
      SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
```

### Manual Deployment

1. Go to **Actions** tab in your repository
2. Select **Terraform Apply Template**
3. Click **Run workflow**
4. Configure parameters:
   - **Environment**: dev, staging, or production
   - **Action**: plan, apply, or destroy
   - **Auto-approve**: Skip manual approval (dev/staging only)

## ⚙️ Configuration

### Input Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `environment` | Target environment (dev/staging/production) | `dev` | ✅ |
| `terraform_version` | Terraform version to use | `1.6.0` | ❌ |
| `working_directory` | Directory containing Terraform files | `./terraform` | ❌ |
| `auto_approve` | Skip manual approval for non-prod | `false` | ❌ |
| `cost_threshold` | Maximum monthly cost in USD | `1000` | ❌ |
| `enable_notifications` | Enable Slack/email notifications | `true` | ❌ |

### Environment Configuration

The template automatically configures environments:

#### Production Environment
- **GitHub Environment**: `project-maestro-gcp`
- **Region**: `us-central1`
- **Instance Range**: 1-20
- **Approval**: Required
- **Security**: Strict validation

#### Staging Environment
- **GitHub Environment**: `project-maestro-staging`
- **Region**: `us-central1`
- **Instance Range**: 0-5
- **Approval**: Optional
- **Security**: Standard validation

#### Development Environment
- **GitHub Environment**: `project-maestro-dev`
- **Region**: `us-central1`
- **Instance Range**: 0-3
- **Approval**: Not required
- **Security**: Basic validation

## 🔐 Security Features

### Pre-deployment Scanning
- **tfsec**: Security scanning for Terraform code
- **Checkov**: Infrastructure compliance validation
- **Format validation**: Ensures code consistency

### Runtime Security
- **State backup**: Automatic backup before apply
- **Drift detection**: Identifies configuration changes
- **Cost monitoring**: Prevents budget overruns
- **Resource tagging**: Ensures proper labeling

### Access Control
- **Environment-based secrets**: Isolated per environment
- **Manual approval gates**: Required for production
- **Workload Identity**: Secure GCP authentication

## 🔄 Rollback Process

### Automatic Rollback
The pipeline automatically triggers rollback on deployment failure:

1. **Detects failure** in apply step
2. **Initializes** Terraform in rollback job
3. **Restores** previous state from backup
4. **Notifies** team of rollback completion

### Manual Rollback
To manually rollback a deployment:

```bash
# Restore from backup
terraform state push .terraform-backups/BACKUP_DIR/terraform.tfstate.backup

# Apply previous configuration
terraform apply -auto-approve previous-config.plan
```

## 📊 Monitoring and Notifications

### Slack Notifications
Configure `SLACK_WEBHOOK` secret to receive:
- ✅ Successful deployments
- ❌ Failed deployments
- 🔄 Rollback notifications
- 💰 Cost alerts

### GitHub Summaries
Automatic deployment summaries include:
- Environment and status
- Function URLs and names
- Cost estimates
- Security scan results

## 🔍 Troubleshooting

### Common Issues

#### Authentication Errors
```
Error: google: could not find default credentials
```
**Solution**: Ensure Workload Identity or service account key is properly configured

#### State Lock Errors
```
Error: Error locking state
```
**Solution**: 
```bash
terraform force-unlock LOCK-ID
```

#### Cost Threshold Exceeded
```
Error: Deployment cost estimate exceeds configured threshold
```
**Solution**: Increase `cost_threshold` parameter or optimize resources

#### Permission Denied
```
Error: Error creating function: googleapi: Error 403
```
**Solution**: Verify service account has required IAM roles:
- `roles/cloudfunctions.admin`
- `roles/iam.serviceAccountUser`
- `roles/storage.admin`

### Debug Mode

Enable debug logging by adding to workflow:

```yaml
env:
  TF_LOG: DEBUG
  TF_LOG_PATH: ./terraform-debug.log
```

## 📚 Examples

### Multi-Environment Deployment Pipeline

```yaml
name: Multi-Environment Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy-dev:
    if: github.event_name == 'pull_request'
    uses: ./.github/workflows/terraform-apply-template.yml
    with:
      environment: 'dev'
      auto_approve: true
    secrets: inherit

  deploy-staging:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [deploy-dev]
    uses: ./.github/workflows/terraform-apply-template.yml
    with:
      environment: 'staging'
      auto_approve: false
    secrets: inherit

  deploy-production:
    if: github.event_name == 'workflow_dispatch'
    needs: [deploy-staging]
    uses: ./.github/workflows/terraform-apply-template.yml
    with:
      environment: 'production'
      auto_approve: false
      cost_threshold: 500
    secrets: inherit
```

### Custom Cost Monitoring

```yaml
jobs:
  deploy-with-cost-check:
    uses: ./.github/workflows/terraform-apply-template.yml
    with:
      environment: 'production'
      cost_threshold: 100  # Strict budget
      enable_notifications: true
    secrets: inherit
```

## 🎯 Best Practices

### Environment Promotion
1. **Dev**: Automatic deployment on PR
2. **Staging**: Manual approval on merge to main
3. **Production**: Manual workflow dispatch only

### Security Hardening
1. Use **Workload Identity Federation** instead of service account keys
2. Enable **branch protection** on main branch
3. Require **PR reviews** before merge
4. Regular **secret rotation**

### Cost Management
1. Set appropriate **cost thresholds** per environment
2. Monitor **monthly spend** trends
3. Use **auto-scaling** configurations
4. Regular **resource cleanup**

### State Management
1. Use **remote state** backend (GCS)
2. Enable **state locking**
3. Regular **state backups**
4. **Version control** state files

## 🤝 Contributing

To improve this template:

1. **Fork** the repository
2. **Create** feature branch
3. **Test** changes in dev environment
4. **Submit** pull request
5. **Update** documentation

## 📄 License

This template is provided under the MIT License. See LICENSE file for details.

## 🆘 Support

For issues and questions:
- **GitHub Issues**: Repository issue tracker
- **Discussions**: GitHub Discussions tab
- **Documentation**: This README and inline comments