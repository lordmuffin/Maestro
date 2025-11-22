# V2V2B Interrogator - Terraform Deployment

Infrastructure-as-Code deployment for the V2V2B Interrogator Google Chat bot.

## 📁 Directory Structure

```
terraform/
├── main.tf                      # Main Terraform configuration
├── variables.tf                 # Variable definitions
├── outputs.tf                   # Output values
├── backend.tf                   # State backend configuration
├── terraform.tfvars.example     # Example variables file
├── .gitignore                   # Terraform-specific gitignore
└── README.md                    # This file
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Terraform (if not already installed)
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Windows
choco install terraform

# Verify installation
terraform version
```

### 2. Authenticate with GCP

```bash
gcloud auth application-default login
```

### 3. Configure Variables

```bash
# Copy the example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

Required variables:
- `gcp_project` - Your GCP project ID
- `github_token` - GitHub Personal Access Token
- `repo_name` - GitHub repository (username/repo)

### 4. Initialize Terraform

```bash
terraform init
```

### 5. Plan Deployment

```bash
terraform plan
```

### 6. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted to confirm.

### 7. Get Function URL

After deployment:

```bash
terraform output function_url
```

### 8. Update Function URL (First Deployment Only)

```bash
# Add to terraform.tfvars
echo 'function_url = "$(terraform output -raw function_url)"' >> terraform.tfvars

# Apply again to update the environment variable
terraform apply
```

## 📊 Terraform Commands

### Basic Operations

```bash
# Initialize (first time or after backend changes)
terraform init

# Format configuration files
terraform fmt

# Validate configuration
terraform validate

# Plan changes
terraform plan

# Apply changes
terraform apply

# Destroy all resources
terraform destroy

# Show current state
terraform show

# List resources
terraform state list
```

### Working with Outputs

```bash
# Show all outputs
terraform output

# Show specific output
terraform output function_url

# Get raw value (no quotes)
terraform output -raw function_url

# Output as JSON
terraform output -json
```

### State Management

```bash
# Refresh state
terraform refresh

# Import existing resource
terraform import google_cloudfunctions2_function.v2v2b_interrogator projects/PROJECT/locations/REGION/functions/FUNCTION_NAME

# Remove resource from state (without destroying)
terraform state rm google_cloudfunctions2_function.v2v2b_interrogator
```

## 🔧 Configuration Options

### Resource Sizing

```hcl
# In terraform.tfvars
memory             = "1Gi"      # Increase memory
timeout_seconds    = 900        # 15 minutes
max_instance_count = 100        # Scale up to 100 instances
min_instance_count = 1          # Always keep 1 instance warm
```

### Cost Optimization

```hcl
# Minimal cost configuration
memory             = "256Mi"
timeout_seconds    = 300
max_instance_count = 5
min_instance_count = 0          # Scale to zero
```

### High Performance

```hcl
# High-traffic configuration
memory             = "2Gi"
timeout_seconds    = 540
max_instance_count = 1000
min_instance_count = 5          # Pre-warmed instances
```

## 🗄️ Backend Configuration

### Option 1: GCS Backend (Recommended)

```bash
# Create state bucket
gsutil mb gs://your-terraform-state-bucket
gsutil versioning set on gs://your-terraform-state-bucket

# Uncomment GCS backend in backend.tf
# Then migrate state
terraform init -migrate-state
```

### Option 2: Terraform Cloud

```bash
# Sign up at https://app.terraform.io
# Create organization and workspace
# Update backend.tf with your details
terraform login
terraform init
```

### Option 3: Local State (Default)

No setup required - state stored in `terraform.tfstate`

⚠️ **Not recommended for production or team collaboration**

## 📝 Outputs

After successful deployment, you'll see:

```
Outputs:

deployment_summary = <<-EOT
================================================================
V2V2B Interrogator Deployment Summary
================================================================

Function Name:    v2v2b-interrogator
Function URL:     https://us-central1-project.cloudfunctions.net/v2v2b-interrogator
Region:           us-central1
Service Account:  v2v2b-interrogator-sa@project.iam.gserviceaccount.com

================================================================
Next Steps:
================================================================
...
EOT

function_name = "v2v2b-interrogator"
function_url = "https://us-central1-project.cloudfunctions.net/v2v2b-interrogator"
google_chat_webhook_url = "https://us-central1-project.cloudfunctions.net/v2v2b-interrogator"
```

## 🔍 Troubleshooting

### Terraform Init Fails

```bash
# Clear .terraform directory
rm -rf .terraform .terraform.lock.hcl
terraform init
```

### API Not Enabled Error

```bash
# Terraform should enable APIs automatically, but if needed:
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### State Lock Error

```bash
# For GCS backend
gsutil rm gs://your-bucket/v2v2b-interrogator/state/default.tflock

# Then retry
terraform apply
```

### Resource Already Exists

```bash
# Import existing resource
terraform import google_cloudfunctions2_function.v2v2b_interrogator \
  projects/PROJECT/locations/REGION/functions/FUNCTION_NAME
```

### Firestore Database Already Exists

The configuration handles this automatically with `ignore_changes` lifecycle rule.

## 🔐 Security Best Practices

### 1. Use Secret Manager (Recommended)

Instead of putting `github_token` in terraform.tfvars:

```bash
# Store in Secret Manager
echo -n "ghp_your_token" | gcloud secrets create github-token --data-file=-

# Update main.tf to use secret
# environment_variables = {
#   GITHUB_TOKEN = data.google_secret_manager_secret_version.github_token.secret_data
# }
```

### 2. State File Security

```bash
# For GCS backend, restrict access
gsutil iam ch -d allUsers gs://your-terraform-state-bucket
gsutil iam ch serviceAccount:terraform@project.iam.gserviceaccount.com:roles/storage.objectAdmin gs://your-terraform-state-bucket
```

### 3. Restrict Function Access

To disable public access and use authentication:

```hcl
# Comment out in main.tf:
# resource "google_cloud_run_service_iam_member" "public_access" { ... }

# Add authenticated invoker instead
```

## 📊 Cost Management

### Estimate Costs

```bash
# Use Google Cloud Pricing Calculator
# Or install infracost
brew install infracost
infracost breakdown --path .
```

### Monitor Costs

```bash
# View function invocations
gcloud functions describe v2v2b-interrogator \
  --gen2 \
  --region=us-central1 \
  --format='value(serviceConfig.availableMemory)'

# View billing
gcloud beta billing accounts list
```

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
name: Terraform Deploy
on:
  push:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-terraform@v2
      - name: Terraform Init
        run: terraform init
        working-directory: ./terraform
      - name: Terraform Apply
        run: terraform apply -auto-approve
        working-directory: ./terraform
        env:
          GOOGLE_CREDENTIALS: ${{ secrets.GCP_CREDENTIALS }}
          TF_VAR_github_token: ${{ secrets.GITHUB_TOKEN }}
```

### GitLab CI

```yaml
terraform:
  image: hashicorp/terraform:latest
  script:
    - cd terraform
    - terraform init
    - terraform apply -auto-approve
  only:
    - main
```

## 📚 Additional Resources

- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

## 🆘 Support

For issues:
1. Check `terraform plan` output
2. Review error messages carefully
3. Check GCP quotas and permissions
4. Verify all required variables are set
