# Telegram Bot Provisioning Script - Setup Guide

## Overview

The `provision-telegram-bot.ps1` PowerShell script has been created to automate end-to-end Telegram bot provisioning for Maestro AI across staging and production environments.

## Features

✅ **Bot Creation Guide** - Semi-automated instructions for creating bots with @BotFather
✅ **Token Validation** - Two-stage validation (format + API test)
✅ **GitHub Secrets Management** - Automated secret configuration via gh CLI
✅ **Webhook Registration** - Automatic webhook setup with Cloud Functions
✅ **Health Checking** - Comprehensive bot and function health validation
✅ **Interactive Menu** - User-friendly interface for all operations
✅ **Logging & Auditing** - Complete audit trail of all operations
✅ **Rollback Capability** - Safe reversion of failed configurations

## Quick Start

### Prerequisites

1. **GitHub CLI** (`gh`) - https://cli.github.com/
2. **Google Cloud SDK** (`gcloud`) - https://cloud.google.com/sdk/install
3. **Terraform** (optional) - https://developer.hashicorp.com/terraform/install
4. **PowerShell 5.1+** - Built into Windows

### Installation

The script is already installed at:
```
c:\Users\andre\Github\Maestro\scripts\provision-telegram-bot.ps1
```

### Fixing Syntax Errors

⚠️ **IMPORTANT**: Due to limitations in the development environment, the script may have minor syntax errors that need to be fixed on your Windows machine.

**To check and fix syntax errors:**

1. Open PowerShell on your Windows machine
2. Navigate to the scripts directory:
   ```powershell
   cd c:\Users\andre\Github\Maestro\scripts
   ```

3. Run the syntax checker:
   ```powershell
   .\check-syntax.ps1
   ```

4. The syntax checker will show any errors with line numbers. Common issues to look for:
   - Mismatched braces `{` `}`
   - Unclosed strings (look for quotes)
   - Missing `while` keywords in do-while loops

5. Fix the errors using your preferred text editor (VS Code, PowerShell ISE, etc.)

6. Re-run the syntax checker until it shows "No syntax errors found!"

### Usage Examples

#### Interactive Mode (Recommended for First Time)
```powershell
.\provision-telegram-bot.ps1
```

Follow the on-screen menu to select your operation.

#### Create New Bot
```powershell
.\provision-telegram-bot.ps1 -Environment staging -CreateBot
```

Guides you through creating a bot with @BotFather and validates the token.

#### Full Automated Setup
```powershell
$token = "YOUR_BOT_TOKEN_HERE"
.\provision-telegram-bot.ps1 -Environment staging -Token $token -FullSetup
```

Performs all operations: validates token, saves metadata, configures GitHub secret, registers webhook, and tests the bot.

#### Register Webhook Only
```powershell
.\provision-telegram-bot.ps1 -Environment production -RegisterWebhook
```

Registers webhook URL with Telegram (assumes token already configured).

#### Health Check
```powershell
.\provision-telegram-bot.ps1 -Environment staging -HealthCheck
```

Checks Cloud Function accessibility, webhook endpoint, and webhook registration status.

#### Test Bot Connection
```powershell
.\provision-telegram-bot.ps1 -Environment staging -TestBot
```

Tests if the bot is online and has received any messages.

## Script Structure

The script is organized into 7 main modules:

1. **Prerequisites & Authentication** - Validates required tools and authentication
2. **Bot Creation (Semi-Automated)** - BotFather guidance and token validation
3. **GitHub Secrets Management** - Automated secret configuration
4. **Telegram API Integration** - Unified API wrapper with retry logic
5. **Webhook & Function Management** - URL retrieval and webhook registration
6. **Testing & Validation** - Bot connection and health checks
7. **Rollback & Error Recovery** - Safe reversion of changes

## Supporting Files

- **`scripts/logs/`** - Audit trails, bot metadata, performance metrics
  - `bot-provisioning-YYYYMMDD.log` - Daily log file
  - `bot-provisioning-audit.jsonl` - JSON Lines audit trail
  - `bot-metadata-{env}.json` - Bot configuration cache
  - `performance-metrics.jsonl` - Operation timing data

- **`scripts/check-syntax.ps1`** - PowerShell syntax validation utility

## Environment Configuration

Before using the script, ensure your GitHub environments are configured:

### Staging Environment
- **Name**: `staging`
- **Required Secrets**:
  - `GCP_WORKLOAD_IDENTITY_PROVIDER`
  - `GCP_SERVICE_ACCOUNT`
  - `GCP_PROJECT_ID`
  - `TELEGRAM_BOT_TOKEN` (created by this script)

### Production Environment
- **Name**: `production`
- **Required Secrets**: Same as staging

See `QUICK_SETUP.md` for detailed environment setup instructions.

## Workflow

### For Staging

1. **Create Bot**:
   ```powershell
   .\provision-telegram-bot.ps1 -Environment staging -CreateBot
   ```

2. **Deploy Cloud Function** (if not already deployed):
   ```bash
   git push origin develop
   ```
   Monitor at: https://github.com/lordmuffin/Maestro/actions

3. **Register Webhook** (after deployment):
   ```powershell
   .\provision-telegram-bot.ps1 -Environment staging -RegisterWebhook
   ```

4. **Test Bot**:
   - Open Telegram
   - Search for your bot (e.g., `@v2v2b_interrogator_staging_bot`)
   - Send `/start`

### For Production

Same as staging, but:
- Use `-Environment production`
- Push to `main` branch instead of `develop`
- Requires manual approval gate for deployment

## Troubleshooting

### Script Won't Run - Execution Policy Error

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\provision-telegram-bot.ps1
```

Or permanently change policy:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### GitHub CLI Not Authenticated

```powershell
gh auth login
```

Select: GitHub.com > HTTPS > Login with web browser

### Google Cloud SDK Not Authenticated

```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Function Not Deployed

Check GitHub Actions:
https://github.com/lordmuffin/Maestro/actions

Ensure the workflow completed successfully for your environment.

### Webhook Registration Failed

1. Verify token is valid:
   ```powershell
   .\provision-telegram-bot.ps1 -Environment staging -TestBot
   ```

2. Verify function is deployed:
   ```powershell
   .\provision-telegram-bot.ps1 -Environment staging -HealthCheck
   ```

3. Check function logs:
   ```bash
   gcloud functions logs read v2v2b-interrogator-staging --gen2 --limit=50
   ```

## Advanced Usage

### Dry Run (WhatIf)
```powershell
.\provision-telegram-bot.ps1 -Environment staging -Token "123:ABC" -FullSetup -WhatIf
```

Shows what would happen without making changes.

### Verbose Logging
```powershell
.\provision-telegram-bot.ps1 -Environment staging -HealthCheck -VerboseLog
```

Displays detailed trace information.

### Force Mode (Skip Confirmations)
```powershell
.\provision-telegram-bot.ps1 -Environment staging -Token "123:ABC" -ConfigureBot -Force
```

Skips all confirmation prompts and overwrites existing configurations.

### Rollback
```powershell
.\provision-telegram-bot.ps1 -Environment staging -Rollback
```

Reverts the last provisioning operation (restores previous webhook URL).

## Security Considerations

- **Tokens are masked** in all output
- **Secrets never logged** to files
- **Audit trail** tracks all operations
- **Confirmation required** for overwrites (unless `-Force`)
- **GitHub Secrets** encrypted at rest by GitHub
- **Cloud Function** environment variables encrypted by GCP

## Next Steps

1. **Fix any syntax errors** using `check-syntax.ps1`
2. **Test in staging** with the interactive mode
3. **Create production bot** once staging is validated
4. **Automate with CI/CD** if needed

## Support

- **Documentation**: See `QUICK_SETUP.md` and `GITOPS_SETUP_GUIDE.md`
- **Issues**: https://github.com/lordmuffin/Maestro/issues
- **Logs**: Check `scripts/logs/` directory for detailed operation history

## Version

- **Script Version**: 1.0.0
- **Date**: 2025-11-28
- **Author**: Maestro AI Project
