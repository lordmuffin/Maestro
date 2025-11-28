# V2V2B Interrogator - Terraform Deployment

Infrastructure-as-Code deployment for the V2V2B Interrogator: An AI-powered system that auto-processes transcripts from Google Drive, creates interrogation PRs, builds a knowledge base, and syncs to Obsidian.

## ✨ Features

- 🤖 **Telegram Bot** - Sarcastic Enterprise Architect conducting technical interviews
- 📂 **Google Drive Monitor** - Auto-detects new transcript files (.txt, .m4a)
- 🎙️ **Audio Transcription** - Converts .m4a files to text using Gemini AI
- 🧠 **AI Analysis** - Extracts insights, patterns, and technical concepts
- ❓ **Interrogation PRs** - Creates GitHub PRs with probing questions
- 📚 **Knowledge Base** - Indexes all content in Firestore for RAG
- 📝 **Obsidian Sync** - Auto-syncs summaries to your Obsidian vault
- 🔍 **Multimodal** - Processes text, audio, and images

## 📁 Directory Structure

```
terraform/
├── main.tf                      # Main Terraform configuration
├── main.py                      # Cloud Function source code
├── requirements.txt             # Python dependencies
├── variables.tf                 # Variable definitions
├── outputs.tf                   # Output values
├── backend.tf                   # State backend configuration
├── terraform.tfvars.example     # Example variables file
├── .gitignore                   # Terraform-specific gitignore
└── README.md                    # This file
```

## 🚀 Quick Start

> **📌 GitHub Actions Deployment**: For CI/CD deployment via GitHub Actions, see [GitHub Configuration Guide](../.github/CONFIGURATION.md) for setting up secrets and environment variables.

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
- `telegram_bot_token` - Telegram Bot Token from @BotFather
- `repo_name` - GitHub repository (username/repo)

Optional Google Drive variables:
- `google_drive_folder_id` - Drive folder ID to monitor for transcripts
- `obsidian_drive_folder_id` - Drive folder ID for Obsidian vault
- `drive_poll_interval` - Polling interval in seconds (default: 300)

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

## 🤖 Telegram Bot Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the prompts:
   - Choose a **display name** (e.g., "V2V2B Interrogator")
   - Choose a **username** (must end in 'bot', e.g., "v2v2b_interrogator_bot")
4. **Save the bot token** - you'll need this for the next step

Example token format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### 2. Configure the Bot Token

Add the bot token to your `terraform.tfvars`:

```hcl
telegram_bot_token = "YOUR_BOT_TOKEN_FROM_BOTFATHER"
```

**For GitHub Actions**: Add as a repository secret named `TELEGRAM_BOT_TOKEN`

### 3. Register the Webhook

After deployment, register your Cloud Function URL as the webhook:

```bash
# Get your function URL
FUNCTION_URL=$(terraform output -raw function_url)

# Get your bot token from terraform.tfvars or environment
BOT_TOKEN="your_bot_token_here"

# Register the webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${FUNCTION_URL}/telegram"
```

**Expected response:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### 4. Verify Webhook Setup

```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

**Expected response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://your-function-url/telegram",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### 5. Test the Bot

1. Open Telegram
2. Search for your bot by username (e.g., `@v2v2b_interrogator_bot`)
3. Send `/start` to begin
4. The bot should respond with a welcome message

### Available Commands

- `/start` - Show welcome message and available commands
- `/help` - Display help information
- `/upload` - Get upload link for audio/images
- `/done` - Complete session and create GitHub PR
- Send any text - Start technical interview conversation

### Troubleshooting

**Bot not responding:**
```bash
# Check function logs
gcloud functions logs read v2v2b-interrogator --region=us-central1 --gen2 --limit=50

# Check webhook status
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"

# Test function health
curl "${FUNCTION_URL}/"
```

**Reset webhook:**
```bash
# Delete webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"

# Set again
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${FUNCTION_URL}/telegram"
```

## 📂 Google Drive Setup (Optional)

### Enable Automatic Transcript Processing

#### 1. Get Google Drive Folder IDs

```bash
# Option 1: From the URL
# https://drive.google.com/drive/folders/FOLDER_ID_HERE
# Copy the FOLDER_ID_HERE part

# Option 2: Using gcloud
gcloud alpha storage ls --folders
```

#### 2. Configure Drive Access

**IMPORTANT**: Google Drive access is granted by sharing folders, not through project IAM roles.

The Cloud Function's service account needs access to your Drive folders:

```bash
# Get the service account email
terraform output service_account_email

# Example output: v2v2b-interrogator-sa@your-project.iam.gserviceaccount.com
```

**Share your Drive folders with this service account**:
1. Open Google Drive in your browser
2. Navigate to your transcript folder
3. Right-click the folder → Share
4. Add the service account email (from above) with **"Viewer"** access
5. Repeat for your Obsidian folder with **"Editor"** access

**Why this is required**:
- There is no project-level IAM role for Drive access
- Access must be granted on specific folders
- The service account acts like a regular user that needs folder permissions

#### 3. Add to terraform.tfvars

```hcl
google_drive_folder_id   = "YOUR_TRANSCRIPT_FOLDER_ID"
obsidian_drive_folder_id = "YOUR_OBSIDIAN_FOLDER_ID"
```

#### 4. Redeploy

```bash
terraform apply
```

### Test Drive Integration

```bash
# Get your function URL
FUNCTION_URL=$(terraform output -raw function_url)

# Manually trigger a scan
curl "$FUNCTION_URL?mode=scan"

# Check the response
# Should show: {"success": true, "processed": N, "results": [...]}
```

### Workflow

1. **Upload** a `.txt` or `.m4a` file to your Drive folder
2. **Trigger** scan manually (`GET /?mode=scan`) or wait for webhook
3. **Processing**:
   - File downloaded from Drive
   - Audio transcribed (if .m4a)
   - AI analyzes content
   - Questions generated
4. **Outputs**:
   - ✅ GitHub PR created with interrogation questions
   - ✅ Summary synced to Obsidian vault
   - ✅ Content indexed in knowledge base

## 🌐 API Endpoints

Once deployed, your Cloud Function exposes these endpoints:

### Health Check
```bash
GET /
```
Returns service status and available endpoints.

### Telegram Webhook
```bash
POST /telegram
Content-Type: application/json
```
Receives Telegram Update events for interactive conversations.

### Upload UI
```bash
GET /?mode=ui&session=SESSION_ID
```
Web interface for uploading audio/image files for analysis.

### File Upload
```bash
POST /?mode=upload&session=SESSION_ID
Content-Type: multipart/form-data
```
Processes uploaded files and analyzes with Gemini AI.

### Drive Scan (Manual Trigger)
```bash
GET /?mode=scan
```
Manually trigger scanning of Google Drive folder for new transcripts.

**Example:**
```bash
curl "https://v2v2b-interrogator-xxx.a.run.app/?mode=scan"
```

**Response:**
```json
{
  "success": true,
  "processed": 2,
  "results": [
    {
      "filename": "meeting-notes.txt",
      "pr_url": "https://github.com/user/repo/pull/123",
      "obsidian_file_id": "1abc..."
    }
  ]
}
```

### Drive Webhook
```bash
POST /?mode=drive_webhook
```
Receives Google Drive push notifications (setup required).

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

## 🗄️ Firestore Collections

The system uses these Firestore collections:

### `sessions`
Stores Google Chat conversation history.

**Document Structure:**
```javascript
{
  session_id: "user@example.com_2025-01-22",
  space_name: "spaces/ABC123",
  history: [
    {
      role: "user",
      content: "Tell me about...",
      timestamp: "2025-01-22T10:00:00Z"
    }
  ],
  created_at: Timestamp,
  last_updated: Timestamp
}
```

### `knowledge_base`
Indexed transcripts for RAG and search.

**Document Structure:**
```javascript
{
  file_id: "1abc123...",
  filename: "meeting-notes.txt",
  content: "Full transcript text...",
  summary: "AI-generated summary...",
  metadata: {
    mimeType: "text/plain",
    createdTime: "2025-01-22T...",
    size: 12345
  },
  indexed_at: Timestamp,
  file_type: "text/plain"
}
```

### `processed_files`
Tracks which files have been processed to prevent duplicates.

**Document Structure:**
```javascript
{
  file_id: "1abc123...",
  processed_at: Timestamp
}
```

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

### GitHub Actions (Recommended)

This repository includes a complete GitHub Actions workflow for automated Terraform deployment.

**Setup Guide**: See [../.github/CONFIGURATION.md](../.github/CONFIGURATION.md) for detailed instructions.

**Quick Setup**:
1. Configure GitHub Secrets:
   - `GCP_PROJECT_ID` - Your GCP project ID
   - `GH_TOKEN` - GitHub Personal Access Token
   - `GCP_WORKLOAD_IDENTITY_PROVIDER` - Workload Identity provider
   - `GCP_SERVICE_ACCOUNT` - Service account email
   - (Optional) `GOOGLE_DRIVE_FOLDER_ID`, `OBSIDIAN_DRIVE_FOLDER_ID`

2. Push to main branch or use workflow dispatch:
   ```bash
   git push origin main
   ```

3. The workflow will:
   - ✅ Validate configuration
   - ✅ Import existing resources
   - ✅ Run Terraform plan
   - ✅ Apply changes (on main branch)
   - ✅ Output function URL

**Workflow Features**:
- Automatic resource import (prevents 409 errors)
- Centralized configuration via GitHub secrets
- PR plan comments
- Security scanning (tfsec, Checkov)
- Workload Identity Federation (no keys needed)

### GitLab CI

```yaml
terraform:
  image: hashicorp/terraform:latest
  variables:
    TF_VAR_gcp_project: $GCP_PROJECT_ID
    TF_VAR_github_token: $GITHUB_TOKEN
    TF_VAR_repo_name: $CI_PROJECT_PATH
  script:
    - cd terraform
    - terraform init
    - terraform apply -auto-approve
  only:
    - main
```

## 🐛 Google Drive Troubleshooting

### Drive API Permission Denied

```bash
# Verify Drive API is enabled
gcloud services list --enabled | grep drive

# Enable if needed
gcloud services enable drive.googleapis.com

# Check service account has Drive access
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:SA_EMAIL"
```

### Files Not Being Processed

1. **Check folder ID is correct**:
   ```bash
   # Test with Drive API
   curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     "https://www.googleapis.com/drive/v3/files/FOLDER_ID"
   ```

2. **Verify service account has access**:
   - Open Drive folder in browser
   - Check if service account email is in "Shared with" list
   - Should have at least "Viewer" access

3. **Check function logs**:
   ```bash
   gcloud functions logs read v2v2b-interrogator \
     --gen2 \
     --region=us-central1 \
     --limit=50
   ```

4. **Test scan endpoint**:
   ```bash
   FUNCTION_URL=$(terraform output -raw function_url)
   curl -v "$FUNCTION_URL?mode=scan"
   ```

### Obsidian Sync Not Working

1. **Verify Obsidian folder ID**:
   ```bash
   # Should be different from transcript folder
   echo $OBSIDIAN_DRIVE_FOLDER_ID
   ```

2. **Check service account has write access**:
   - Service account needs "Editor" role on Obsidian folder
   - Check folder sharing settings

3. **View created files**:
   ```bash
   # List files in Obsidian folder
   gcloud alpha storage ls gs://BUCKET/obsidian/
   ```

### Duplicate Processing

Files are tracked in `processed_files` collection. To reset:

```python
# Using Firebase Console or Python
from google.cloud import firestore
db = firestore.Client()
db.collection('processed_files').document('FILE_ID').delete()
```

## 📚 Additional Resources

- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [Google Drive API](https://developers.google.com/drive/api/guides/about-sdk)
- [Gemini AI Documentation](https://ai.google.dev/docs)
- [Firestore Documentation](https://cloud.google.com/firestore/docs)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

## 🆘 Support

For issues:
1. Check `terraform plan` output
2. Review error messages carefully
3. Check GCP quotas and permissions
4. Verify all required variables are set
