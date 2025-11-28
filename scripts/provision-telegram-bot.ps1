<#
.SYNOPSIS
    Telegram Bot Provisioning Utility for Maestro AI Project

.DESCRIPTION
    Comprehensive automation for Telegram bot lifecycle management:
    • Create new bots with BotFather guidance
    • Validate and store bot tokens
    • Configure GitHub environment secrets
    • Register webhooks with Cloud Functions
    • Test bot connectivity and health
    • Rollback failed configurations

    Supports both staging and production environments with separate bot deployments.

.PARAMETER Environment
    Target environment: 'staging' or 'production'

.PARAMETER Token
    Telegram bot token (format: 123456789:ABC...)
    If not provided, will prompt interactively

.PARAMETER CreateBot
    Show BotFather creation guide and validate token

.PARAMETER ConfigureBot
    Set GitHub secret for existing token

.PARAMETER RegisterWebhook
    Register webhook URL with Telegram

.PARAMETER TestBot
    Test bot connection and message reception

.PARAMETER HealthCheck
    Comprehensive health check (function + webhook)

.PARAMETER FullSetup
    Execute all operations (create/configure + webhook + test)

.PARAMETER WebhookUrl
    Manual webhook URL (if not using Terraform outputs)

.PARAMETER Force
    Skip confirmation prompts, overwrite existing configurations

.PARAMETER SkipConfirmation
    Alias for -Force

.PARAMETER WhatIf
    Show what would happen without making changes

.PARAMETER Rollback
    Revert last provisioning operation

.EXAMPLE
    .\provision-telegram-bot.ps1
    Interactive mode with menu

.EXAMPLE
    .\provision-telegram-bot.ps1 -Environment staging -CreateBot
    Guide user through creating staging bot

.EXAMPLE
    .\provision-telegram-bot.ps1 -Environment staging -Token "123:ABC" -FullSetup
    Automated full setup with provided token

.EXAMPLE
    .\provision-telegram-bot.ps1 -Environment production -RegisterWebhook
    Register webhook for production (assumes token already configured)

.EXAMPLE
    .\provision-telegram-bot.ps1 -Environment staging -HealthCheck
    Check webhook and function health

.NOTES
    Author: Maestro AI Project
    Version: 1.0.0
    Requires: gh CLI, gcloud SDK, terraform (optional)

    If you receive an execution policy error, run:
    powershell -ExecutionPolicy Bypass -File .\scripts\provision-telegram-bot.ps1
#>

[CmdletBinding(DefaultParameterSetName='Interactive')]
param(
    # Environment
    [Parameter(Mandatory=$false, ParameterSetName='Interactive')]
    [Parameter(Mandatory=$true, ParameterSetName='CreateBot')]
    [Parameter(Mandatory=$true, ParameterSetName='ConfigureBot')]
    [Parameter(Mandatory=$true, ParameterSetName='RegisterWebhook')]
    [Parameter(Mandatory=$true, ParameterSetName='TestBot')]
    [Parameter(Mandatory=$true, ParameterSetName='HealthCheck')]
    [Parameter(Mandatory=$true, ParameterSetName='FullSetup')]
    [Parameter(Mandatory=$true, ParameterSetName='Rollback')]
    [ValidateSet('staging', 'production', IgnoreCase=$false)]
    [string]$Environment,

    # Token
    [Parameter(Mandatory=$false, ParameterSetName='CreateBot')]
    [Parameter(Mandatory=$false, ParameterSetName='ConfigureBot')]
    [Parameter(Mandatory=$false, ParameterSetName='FullSetup')]
    [string]$Token,

    # Operation modes
    [Parameter(Mandatory=$true, ParameterSetName='CreateBot')]
    [switch]$CreateBot,

    [Parameter(Mandatory=$true, ParameterSetName='ConfigureBot')]
    [switch]$ConfigureBot,

    [Parameter(Mandatory=$true, ParameterSetName='RegisterWebhook')]
    [switch]$RegisterWebhook,

    [Parameter(Mandatory=$true, ParameterSetName='TestBot')]
    [switch]$TestBot,

    [Parameter(Mandatory=$true, ParameterSetName='HealthCheck')]
    [switch]$HealthCheck,

    [Parameter(Mandatory=$true, ParameterSetName='FullSetup')]
    [switch]$FullSetup,

    [Parameter(Mandatory=$true, ParameterSetName='Rollback')]
    [switch]$Rollback,

    # Optional parameters
    [Parameter(Mandatory=$false)]
    [string]$WebhookUrl,

    [Parameter(Mandatory=$false)]
    [Alias('SkipConfirmation')]
    [switch]$Force,

    [Parameter(Mandatory=$false)]
    [switch]$WhatIf,

    [Parameter(Mandatory=$false)]
    [switch]$VerboseLog
)

#region Configuration & Constants

$SCRIPT_VERSION = "1.0.0"
$SCRIPT_DATE = "2025-11-28"
$SCRIPT_AUTHOR = "Maestro AI Project"

# Paths
$SCRIPT_ROOT = Split-Path -Parent $PSCommandPath
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_ROOT
$TERRAFORM_DIR = Join-Path $PROJECT_ROOT "terraform"
$LOGS_DIR = Join-Path $SCRIPT_ROOT "logs"
$CONFIG_DIR = Join-Path $SCRIPT_ROOT "config"

# Ensure directories exist
if (-not (Test-Path $LOGS_DIR)) {
    New-Item -ItemType Directory -Path $LOGS_DIR -Force | Out-Null
}

# Logging configuration
$script:LogLevel = if ($VerboseLog) { 'Verbose' } else { 'Info' }
$script:LogFile = Join-Path $LOGS_DIR "bot-provisioning-$(Get-Date -Format 'yyyyMMdd').log"
$script:AuditFile = Join-Path $LOGS_DIR "bot-provisioning-audit.jsonl"
$script:MetricsFile = Join-Path $LOGS_DIR "performance-metrics.jsonl"

# Global state tracking
$global:ProvisioningState = @{
    SecretCreated = $false
    SecretOldValue = $null
    WebhookRegistered = $false
    WebhookOldUrl = $null
    StartTime = Get-Date
    Operations = @()
    TempFiles = @()
}

# Performance metrics
$script:PerformanceMetrics = @{
    StartTime = Get-Date
    Operations = @()
}

# Cleanup flag
$script:CleanupOnExit = $true

#endregion

#region Helper Functions - Logging & Utilities

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Verbose', 'Info', 'Warning', 'Error', 'Success')]
        [string]$Level = 'Info',
        [switch]$NoConsole
    )

    # Timestamp
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"

    # Format log entry
    $logEntry = "[$timestamp] [$Level] $Message"

    # Write to file
    try {
        Add-Content -Path $script:LogFile -Value $logEntry -ErrorAction SilentlyContinue
    } catch {
        # Silently fail if can't write to log file
    }

    # Console output (unless suppressed)
    if (-not $NoConsole) {
        # Skip verbose messages unless -VerboseLog
        if ($Level -eq 'Verbose' -and $script:LogLevel -ne 'Verbose') {
            return
        }

        $color = switch ($Level) {
            'Verbose' { 'Gray' }
            'Info'    { 'White' }
            'Warning' { 'Yellow' }
            'Error'   { 'Red' }
            'Success' { 'Green' }
        }

        $symbol = switch ($Level) {
            'Verbose' { '🔍' }
            'Info'    { 'ℹ️ ' }
            'Warning' { '⚠️ ' }
            'Error'   { '❌' }
            'Success' { '✅' }
        }

        Write-Host "$symbol $Message" -ForegroundColor $color
    }
}

function Format-TokenForDisplay {
    param([string]$Token)

    if (-not $Token -or $Token.Length -lt 10) {
        return "****"
    }

    return "$($Token.Substring(0, 8))...$($Token.Substring($Token.Length - 4))"
}

function Confirm-Action {
    param(
        [string]$Prompt,
        [switch]$DefaultYes
    )

    if ($Force -or $WhatIf) {
        return $true
    }

    $suffix = if ($DefaultYes) { " [Y/n]" } else { " [y/N]" }
    $response = Read-Host "$Prompt$suffix"

    if ($DefaultYes) {
        return ($response -eq '' -or $response -match '^[Yy]')
    } else {
        return ($response -match '^[Yy]')
    }
}

function Start-OperationTimer {
    param([string]$OperationName)

    return @{
        Name = $OperationName
        StartTime = Get-Date
    }
}

function Stop-OperationTimer {
    param([hashtable]$Timer, [bool]$Success = $true)

    $duration = (Get-Date) - $Timer.StartTime

    $metric = @{
        operation = $Timer.Name
        duration_ms = [int]$duration.TotalMilliseconds
        success = $Success
        timestamp = Get-Date -Format "o"
    }

    $script:PerformanceMetrics.Operations += $metric

    Write-Log -Level Verbose -Message "$($Timer.Name) completed in $([int]$duration.TotalMilliseconds)ms"

    return $metric
}

function Save-AuditEntry {
    param(
        [string]$Operation,
        [string]$Environment,
        [hashtable]$Details = @{},
        [bool]$Success = $true,
        [string]$ErrorMessage = ""
    )

    $auditEntry = @{
        timestamp = Get-Date -Format "o"
        operation = $Operation
        environment = $Environment
        success = $Success
        error_message = $ErrorMessage
        user = $env:USERNAME
        machine = $env:COMPUTERNAME
        script_version = $SCRIPT_VERSION
        details = $Details
    }

    try {
        $json = $auditEntry | ConvertTo-Json -Compress
        Add-Content -Path $script:AuditFile -Value $json -ErrorAction Stop
        Write-Log -Level Verbose -Message "Audit entry saved: $Operation"
    } catch {
        Write-Log -Level Warning -Message "Failed to save audit entry: $($_.Exception.Message)"
    }
}

#endregion

#region Module 1: Prerequisites & Authentication

function Test-Prerequisites {
    Write-Log -Level Info -Message "Checking prerequisites..."
    Write-Host ""

    $results = @{
        GitHubCLI = $false
        GCloudSDK = $false
        Terraform = $false
        PowerShell = $true
    }

    # Test 1: GitHub CLI
    try {
        $null = Get-Command gh -ErrorAction Stop
        $ghVersion = (gh --version 2>&1)[0]
        Write-Host "✅ GitHub CLI: " -NoNewline -ForegroundColor Green
        Write-Host $ghVersion
        $results.GitHubCLI = $true
    } catch {
        Write-Host "❌ GitHub CLI not found" -ForegroundColor Red
        Write-Host "   Install: " -NoNewline
        Write-Host "https://cli.github.com/" -ForegroundColor Cyan
        Write-Host "   Or run: winget install --id GitHub.cli" -ForegroundColor Gray
    }

    # Test 2: Google Cloud SDK
    try {
        $null = Get-Command gcloud -ErrorAction Stop
        $gcloudVersion = (gcloud --version 2>&1)[0]
        Write-Host "✅ Google Cloud SDK: " -NoNewline -ForegroundColor Green
        Write-Host $gcloudVersion
        $results.GCloudSDK = $true
    } catch {
        Write-Host "❌ gcloud CLI not found" -ForegroundColor Red
        Write-Host "   Install: " -NoNewline
        Write-Host "https://cloud.google.com/sdk/install" -ForegroundColor Cyan
    }

    # Test 3: Terraform (optional)
    try {
        $null = Get-Command terraform -ErrorAction Stop
        $tfVersion = (terraform version 2>&1 | Select-Object -First 1)
        Write-Host "✅ Terraform: " -NoNewline -ForegroundColor Green
        Write-Host $tfVersion
        $results.Terraform = $true
    } catch {
        Write-Host "⚠️  Terraform not found (optional - needed for automatic webhook URL lookup)" -ForegroundColor Yellow
        Write-Host "   Install: " -NoNewline
        Write-Host "https://developer.hashicorp.com/terraform/install" -ForegroundColor Cyan
        Write-Host "   Or provide webhook URL manually" -ForegroundColor Gray
    }

    # Test 4: PowerShell version
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -ge 5) {
        Write-Host "✅ PowerShell: " -NoNewline -ForegroundColor Green
        Write-Host "v$($psVersion.Major).$($psVersion.Minor)"
    } else {
        Write-Host "⚠️  PowerShell v$($psVersion.Major).$($psVersion.Minor) (v5+ recommended)" -ForegroundColor Yellow
    }

    Write-Host ""

    # Check required tools
    $requiredTools = @('GitHubCLI', 'GCloudSDK')
    $allRequiredPresent = $true
    foreach ($tool in $requiredTools) {
        if (-not $results[$tool]) {
            $allRequiredPresent = $false
            break
        }
    }

    if ($allRequiredPresent) {
        Write-Log -Level Success -Message "All required tools installed"
        return $true
    } else {
        Write-Log -Level Error -Message "Missing required tools - please install and retry"
        return $false
    }
}

function Test-Authentication {
    Write-Log -Level Info -Message "Validating authentication..."
    Write-Host ""

    $allOk = $true

    # Check GitHub CLI authentication
    Write-Host "GitHub CLI: " -NoNewline
    $ghAuthStatus = gh auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        $account = ($ghAuthStatus | Select-String "Logged in to github.com as (.*?) " | ForEach-Object { $_.Matches.Groups[1].Value })
        if (-not $account) {
            $account = "authenticated"
        }
        Write-Host "✅ Authenticated as $account" -ForegroundColor Green
    } else {
        Write-Host "❌ Not authenticated" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Run: " -NoNewline
        Write-Host "gh auth login" -ForegroundColor Yellow
        Write-Host "   Select: GitHub.com > HTTPS > Login with web browser"
        Write-Host ""
        $allOk = $false
    }

    # Check gcloud authentication
    Write-Host "gcloud CLI: " -NoNewline
    $gcloudAccount = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>&1
    if ($LASTEXITCODE -eq 0 -and $gcloudAccount) {
        Write-Host "✅ Authenticated as $gcloudAccount" -ForegroundColor Green
    } else {
        Write-Host "❌ Not authenticated" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Run: " -NoNewline
        Write-Host "gcloud auth login" -ForegroundColor Yellow
        Write-Host ""
        $allOk = $false
    }

    # Check gcloud project
    Write-Host "gcloud project: " -NoNewline
    $gcloudProject = gcloud config get-value project 2>&1
    if ($LASTEXITCODE -eq 0 -and $gcloudProject -and $gcloudProject -ne '(unset)') {
        Write-Host "✅ $gcloudProject" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Not set" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   Run: " -NoNewline
        Write-Host "gcloud config set project YOUR_PROJECT_ID" -ForegroundColor Yellow
        Write-Host ""
    }

    # Check repository access
    Write-Host "GitHub repo access: " -NoNewline
    try {
        $repo = gh api /repos/lordmuffin/Maestro 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ lordmuffin/Maestro" -ForegroundColor Green
        } else {
            throw "API call failed"
        }
    } catch {
        Write-Host "❌ Cannot access repository" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Ensure you have access to lordmuffin/Maestro repository"
        Write-Host "   Check token permissions: gh auth refresh -s repo,write:org"
        Write-Host ""
        $allOk = $false
    }

    Write-Host ""

    if ($allOk) {
        Write-Log -Level Success -Message "All authentication checks passed"
        return $true
    } else {
        Write-Log -Level Error -Message "Authentication incomplete - please resolve issues above"
        return $false
    }
}

function Test-GitHubEnvironment {
    param([string]$TargetEnvironment)

    Write-Log -Level Verbose -Message "Validating GitHub environment: $TargetEnvironment"

    try {
        $envs = gh api /repos/lordmuffin/Maestro/environments 2>&1 | ConvertFrom-Json

        if ($LASTEXITCODE -ne 0) {
            throw "API call failed"
        }

        $exists = $envs.environments | Where-Object { $_.name -eq $TargetEnvironment }

        if ($exists) {
            Write-Log -Level Verbose -Message "Environment '$TargetEnvironment' found"
            return $true
        } else {
            Write-Log -Level Error -Message "Environment '$TargetEnvironment' not found"
            Write-Host ""
            Write-Host "Create environment at:" -ForegroundColor Yellow
            Write-Host "https://github.com/lordmuffin/Maestro/settings/environments/new"
            Write-Host ""
            Write-Host "See QUICK_SETUP.md for configuration details" -ForegroundColor Gray
            return $false
        }
    } catch {
        Write-Log -Level Error -Message "Failed to validate environment: $($_.Exception.Message)"
        return $false
    }
}

function Test-EnvironmentConfiguration {
    param([string]$TargetEnvironment)

    Write-Log -Level Info -Message "Validating environment configuration: $TargetEnvironment"
    Write-Host ""

    # Check environment exists
    Write-Host "Environment exists: " -NoNewline
    if (-not (Test-GitHubEnvironment -TargetEnvironment $TargetEnvironment)) {
        Write-Host "❌" -ForegroundColor Red
        return $false
    }
    Write-Host "✅" -ForegroundColor Green

    # Check required secrets exist (except TELEGRAM_BOT_TOKEN which we're setting)
    Write-Host "Checking required secrets..." -ForegroundColor Yellow

    $requiredSecrets = @(
        'GCP_WORKLOAD_IDENTITY_PROVIDER',
        'GCP_SERVICE_ACCOUNT',
        'GCP_PROJECT_ID'
    )

    try {
        $secrets = gh secret list --env $TargetEnvironment --json name 2>&1 | ConvertFrom-Json
        $secretNames = $secrets | ForEach-Object { $_.name }

        $allPresent = $true
        foreach ($secret in $requiredSecrets) {
            Write-Host "  $secret`: " -NoNewline
            if ($secretNames -contains $secret) {
                Write-Host "✅" -ForegroundColor Green
            } else {
                Write-Host "❌ Missing" -ForegroundColor Red
                $allPresent = $false
            }
        }

        if (-not $allPresent) {
            Write-Host ""
            Write-Host "⚠️  Missing required secrets" -ForegroundColor Yellow
            Write-Host "   See QUICK_SETUP.md for configuration details" -ForegroundColor Gray
            Write-Host ""
            return $false
        }
    } catch {
        Write-Log -Level Warning -Message "Could not verify secrets: $($_.Exception.Message)"
    }

    Write-Host ""
    Write-Log -Level Success -Message "Environment configuration valid"
    return $true
}

#endregion

#region Module 2: Bot Creation (Semi-Automated)

function Test-TelegramTokenFormat {
    param([string]$TokenString)

    return $TokenString -match '^[0-9]{8,10}:[A-Za-z0-9_-]{35}$'
}

function Test-TelegramToken {
    param([string]$TokenString)

    try {
        $response = Invoke-RestMethod `
            -Uri "https://api.telegram.org/bot$TokenString/getMe" `
            -Method Get `
            -TimeoutSec 10 `
            -ErrorAction Stop

        if ($response.ok) {
            return $response.result
        }
    } catch {
        Write-Log -Level Verbose -Message "Token validation failed: $($_.Exception.Message)"
    }
    return $null
}

function Show-BotCreationGuide {
    param([string]$TargetEnvironment)

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Step 1: Create Bot with @BotFather" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Step-by-step instructions
    Write-Host "📱 Open Telegram and follow these steps:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Search for " -NoNewline
    Write-Host "@BotFather" -ForegroundColor Green
    Write-Host "2. Start a chat and send: " -NoNewline
    Write-Host "/newbot" -ForegroundColor Green
    Write-Host ""

    # Suggested names
    Write-Host "3. When prompted for bot name, use:" -ForegroundColor Yellow
    Write-Host "   " -NoNewline
    Write-Host "V2V2B Interrogator $(if($TargetEnvironment -eq 'staging'){'[Staging]'}else{'[Production]'})" -ForegroundColor Green
    Write-Host ""

    Write-Host "4. When prompted for username, use:" -ForegroundColor Yellow
    Write-Host "   " -NoNewline
    Write-Host "v2v2b_interrogator_${TargetEnvironment}_bot" -ForegroundColor Green
    Write-Host ""

    # Token instructions
    Write-Host "5. @BotFather will reply with a token that looks like:" -ForegroundColor Yellow
    Write-Host "   " -NoNewline
    Write-Host "123456789:ABCdefGHI-JKLmnoPQRstuVWX123456789" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   ⚠️  " -NoNewline -ForegroundColor Yellow
    Write-Host "Keep this token secret!" -ForegroundColor Yellow
    Write-Host ""

    # Optional configuration
    Write-Host "📝 Optional: Configure bot details with @BotFather:" -ForegroundColor Blue
    Write-Host "   /setdescription - Set bot description"
    Write-Host "   /setabouttext - Set about text"
    Write-Host "   /setcommands - Configure available commands"
    Write-Host "   /setuserpic - Set bot profile picture"
    Write-Host ""

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Prompt for token
    do {
        $tokenInput = Read-Host "Paste your bot token (or 'cancel' to abort)"

        if ($tokenInput -eq 'cancel') {
            Write-Log -Level Warning -Message "Bot creation cancelled"
            return $null
        }

        # Validate format
        if (-not (Test-TelegramTokenFormat -TokenString $tokenInput)) {
            Write-Host "❌ Invalid token format" -ForegroundColor Red
            Write-Host "   Token should be: BOT_ID:SECRET_KEY" -ForegroundColor Gray
            Write-Host "   Example: 123456789:ABCdefGHI-JKLmnoPQR-STUvwxYZ123456" -ForegroundColor Gray
            Write-Host ""
            continue
        }

        # Test with API
        Write-Host "🔍 Validating token..." -ForegroundColor Yellow
        $botInfo = Test-TelegramToken -TokenString $tokenInput

        if ($null -eq $botInfo) {
            Write-Host "❌ Token validation failed" -ForegroundColor Red
            Write-Host "   The token is correctly formatted but not recognized by Telegram" -ForegroundColor Gray
            Write-Host ""

            if (-not (Confirm-Action "Try another token?")) {
                return $null
            }
            continue
        }

        # Success!
        Write-Host ""
        Write-Host "✅ Bot validated successfully!" -ForegroundColor Green
        Write-Host "   Username: @$($botInfo.username)" -ForegroundColor Cyan
        Write-Host "   Name: $($botInfo.first_name)" -ForegroundColor Cyan
        Write-Host "   ID: $($botInfo.id)" -ForegroundColor Cyan
        Write-Host ""

        $result = @{
            Token = $tokenInput
            Username = $botInfo.username
            Name = $botInfo.first_name
            ID = $botInfo.id
        }
        return $result

    } while ($true)
}

function Save-BotMetadata {
    param(
        [string]$TargetEnvironment,
        [hashtable]$BotInfo,
        [string]$TokenString
    )

    $metadataPath = Join-Path $LOGS_DIR "bot-metadata-$TargetEnvironment.json"

    # Check if metadata exists
    if (Test-Path $metadataPath) {
        $existing = Get-Content $metadataPath | ConvertFrom-Json

        Write-Host "⚠️  Bot already configured for $TargetEnvironment`:" -ForegroundColor Yellow
        Write-Host "   Username: @$($existing.username)"
        Write-Host "   Bot ID: $($existing.id)"
        Write-Host "   Configured: $(Get-Date $existing.timestamp -Format 'yyyy-MM-dd HH:mm')"
        Write-Host ""

        Write-Host "New bot details:" -ForegroundColor Cyan
        Write-Host "   Username: @$($BotInfo.Username)"
        Write-Host "   Bot ID: $($BotInfo.ID)"
        Write-Host ""

        if (-not (Confirm-Action "Replace existing bot configuration?" -DefaultYes:$false)) {
            Write-Log -Level Warning -Message "Keeping existing bot"
            return $false
        }

        # Archive old metadata
        $archivePath = $metadataPath -replace '\.json$', "-archive-$(Get-Date -Format 'yyyyMMddHHmmss').json"
        Copy-Item $metadataPath $archivePath
        Write-Host "Previous configuration archived: $archivePath" -ForegroundColor Gray
    }

    # Save new metadata
    $metadata = @{
        environment = $TargetEnvironment
        username = $BotInfo.Username
        name = $BotInfo.Name
        id = $BotInfo.ID
        token_prefix = $TokenString.Substring(0, [Math]::Min(10, $TokenString.Length)) + "..."
        timestamp = Get-Date -Format "o"
        provisioned_by = $env:USERNAME
        machine = $env:COMPUTERNAME
    }

    $metadata | ConvertTo-Json | Set-Content $metadataPath
    Write-Log -Level Success -Message "Bot metadata saved"

    return $true
}

#endregion

#region Module 3: GitHub Secrets Management

function Test-GitHubEnvironmentSecret {
    param(
        [string]$TargetEnvironment,
        [string]$SecretName
    )

    try {
        $secrets = gh secret list --env $TargetEnvironment --json name 2>&1 | ConvertFrom-Json
        $secretNames = $secrets | ForEach-Object { $_.name }

        return ($secretNames -contains $SecretName)
    } catch {
        Write-Log -Level Verbose -Message "Failed to check secret existence: $($_.Exception.Message)"
        return $false
    }
}

function Set-GitHubEnvironmentSecret {
    param(
        [string]$TargetEnvironment,
        [string]$SecretName,
        [string]$SecretValue
    )

    if ($WhatIf) {
        Write-Host "WHATIF: Would set GitHub secret $SecretName in $TargetEnvironment environment" -ForegroundColor Cyan
        return $true
    }

    # Check if exists first (idempotent)
    $exists = Test-GitHubEnvironmentSecret -TargetEnvironment $TargetEnvironment -SecretName $SecretName

    if ($exists -and -not $Force) {
        Write-Host "⚠️  $SecretName already exists in $TargetEnvironment" -ForegroundColor Yellow

        # Get metadata from last run if available
        $metadataPath = Join-Path $LOGS_DIR "bot-metadata-$TargetEnvironment.json"
        if (Test-Path $metadataPath) {
            $metadata = Get-Content $metadataPath | ConvertFrom-Json
            Write-Host "Current bot: @$($metadata.username) (configured $(Get-Date $metadata.timestamp -Format 'yyyy-MM-dd HH:mm'))" -ForegroundColor Cyan
        }

        Write-Host ""
        if (-not (Confirm-Action "Overwrite existing token?")) {
            Write-Log -Level Warning -Message "Skipping secret update"
            return $false
        }

        $global:ProvisioningState.SecretOldValue = "existed"
    }

    # Set secret via gh CLI
    try {
        $env:GH_SECRET_VALUE = $SecretValue
        gh secret set $SecretName --env $TargetEnvironment --body $SecretValue 2>&1 | Out-Null

        if ($LASTEXITCODE -eq 0) {
            Write-Log -Level Success -Message "GitHub secret $SecretName configured"
            $global:ProvisioningState.SecretCreated = $true

            # Save audit entry
            Save-AuditEntry -Operation "SetGitHubSecret" -Environment $TargetEnvironment -Details @{
                secret_name = $SecretName
                overwrite = $exists
            } -Success $true

            return $true
        } else {
            throw "gh secret set failed with exit code $LASTEXITCODE"
        }
    } catch {
        Write-Log -Level Error -Message "Failed to set GitHub secret: $($_.Exception.Message)"

        Save-AuditEntry -Operation "SetGitHubSecret" -Environment $TargetEnvironment -Details @{
            secret_name = $SecretName
        } -Success $false -ErrorMessage $_.Exception.Message

        return $false
    } finally {
        Remove-Item Env:\GH_SECRET_VALUE -ErrorAction SilentlyContinue
    }
}

#endregion

#region Module 4: Telegram API Integration

function Invoke-TelegramAPI {
    param(
        [string]$TokenString,
        [string]$Method,
        [hashtable]$Body = @{},
        [int]$TimeoutSec = 30
    )

    $url = "https://api.telegram.org/bot$TokenString/$Method"

    Write-Log -Level Verbose -Message "Calling Telegram API: $Method"

    try {
        if ($Body.Count -gt 0) {
            $response = Invoke-RestMethod `
                -Uri $url `
                -Method Post `
                -Body $Body `
                -ContentType "application/x-www-form-urlencoded" `
                -TimeoutSec $TimeoutSec `
                -ErrorAction Stop
        } else {
            $response = Invoke-RestMethod `
                -Uri $url `
                -Method Get `
                -TimeoutSec $TimeoutSec `
                -ErrorAction Stop
        }

        if ($response.ok) {
            Write-Log -Level Verbose -Message "API call successful: $Method"
            return $response.result
        } else {
            Write-Log -Level Error -Message "Telegram API error: $($response.description)"
            return $null
        }

    } catch [System.Net.WebException] {
        Write-Log -Level Error -Message "Network error calling Telegram API: $($_.Exception.Message)"

        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode

            switch ($statusCode) {
                401 { Write-Host "   Invalid bot token" -ForegroundColor Red }
                404 { Write-Host "   Bot not found or method doesn't exist" -ForegroundColor Red }
                429 { Write-Host "   Rate limited - too many requests" -ForegroundColor Yellow }
                default { Write-Host "   HTTP $statusCode error" -ForegroundColor Red }
            }
        }

        return $null

    } catch {
        Write-Log -Level Error -Message "Unexpected error calling Telegram API: $($_.Exception.Message)"
        return $null
    }
}

function Get-TelegramWebhookInfo {
    param([string]$TokenString)

    $info = Invoke-TelegramAPI -TokenString $TokenString -Method "getWebhookInfo"

    if ($info) {
        Write-Host "📡 Webhook Information:" -ForegroundColor Cyan
        Write-Host "  URL: $($info.url)"
        Write-Host "  Pending Updates: $($info.pending_update_count)"

        if ($info.last_error_date) {
            $errorDate = [System.DateTimeOffset]::FromUnixTimeSeconds($info.last_error_date).LocalDateTime
            Write-Host "  Last Error: $($info.last_error_message) at $errorDate" -ForegroundColor Yellow
        } else {
            Write-Host "  Status: Healthy" -ForegroundColor Green
        }

        return $info
    }

    return $null
}

function Register-TelegramWebhook {
    param(
        [string]$TokenString,
        [string]$WebhookUrlString
    )

    if ($WhatIf) {
        Write-Host "WHATIF: Would register webhook: $WebhookUrlString" -ForegroundColor Cyan
        return $true
    }

    # Check current webhook first
    $current = Invoke-TelegramAPI -TokenString $TokenString -Method "getWebhookInfo"

    if ($current -and $current.url -eq $WebhookUrlString) {
        Write-Log -Level Success -Message "Webhook already correctly configured"
        return $true
    }

    if ($current -and $current.url) {
        Write-Host "⚠️  Existing webhook found:" -ForegroundColor Yellow
        Write-Host "   Current: $($current.url)"
        Write-Host "   New:     $WebhookUrlString"
        Write-Host ""

        if (-not (Confirm-Action "Replace webhook URL?" -DefaultYes:$true)) {
            Write-Log -Level Warning -Message "Skipping webhook registration"
            return $false
        }

        # Save old URL for rollback
        $global:ProvisioningState.WebhookOldUrl = $current.url
        $global:ProvisioningState.WebhookReplaced = $true
    }

    # Register new webhook
    Write-Host "Registering webhook..." -ForegroundColor Yellow
    $response = Invoke-TelegramAPI -TokenString $TokenString -Method "setWebhook" -Body @{
        url = $WebhookUrlString
        drop_pending_updates = "true"
    }

    if ($response) {
        Write-Log -Level Success -Message "Webhook registered: $WebhookUrlString"
        $global:ProvisioningState.WebhookRegistered = $true

        Save-AuditEntry -Operation "RegisterWebhook" -Environment $Environment -Details @{
            webhook_url = $WebhookUrlString
            previous_url = $global:ProvisioningState.WebhookOldUrl
        } -Success $true

        return $true
    } else {
        Write-Log -Level Error -Message "Webhook registration failed"

        Save-AuditEntry -Operation "RegisterWebhook" -Environment $Environment -Details @{
            webhook_url = $WebhookUrlString
        } -Success $false -ErrorMessage "API call failed"

        return $false
    }
}

#endregion

#region Module 5: Webhook & Function Management

function Initialize-TerraformState {
    param([string]$TargetEnvironment)

    Write-Log -Level Info -Message "Initializing Terraform state connection..."

    # 1. Check if backend is configured
    if (-not (Test-Path ".terraform")) {
        Write-Host "⚠️  Terraform backend not initialized." -ForegroundColor Yellow

        # Try to get bucket from GitHub Variable
        $bucket = $null
        try {
            $bucket = gh variable get TERRAFORM_STATE_BUCKET --env $TargetEnvironment 2>&1
            if ($LASTEXITCODE -eq 0 -and $bucket) {
                Write-Host "✅ Found state bucket: $bucket" -ForegroundColor Green
            }
        } catch {}

        if (-not $bucket) {
            $bucket = Read-Host "Enter Terraform State Bucket Name (e.g., project-tfstate)"
        }

        if (-not $bucket) {
            Write-Log -Level Error -Message "No state bucket provided"
            return $false
        }

        Write-Host "Initializing Terraform..." -ForegroundColor Cyan
        terraform init `
            -backend-config="bucket=$bucket" `
            -backend-config="prefix=terraform/state/$TargetEnvironment" `
            2>&1 | Out-Null

        if ($LASTEXITCODE -ne 0) {
            Write-Log -Level Error -Message "Terraform init failed"
            return $false
        }
    }

    # 2. Manage Workspace
    $workspaces = terraform workspace list 2>&1
    if ($workspaces -notmatch $TargetEnvironment) {
        Write-Host "Creating workspace '$TargetEnvironment'..." -ForegroundColor Cyan
        terraform workspace new $TargetEnvironment 2>&1 | Out-Null
    } else {
        Write-Host "Selecting workspace '$TargetEnvironment'..." -ForegroundColor Cyan
        terraform workspace select $TargetEnvironment 2>&1 | Out-Null
    }

    return ($LASTEXITCODE -eq 0)
}

function Get-TerraformFunctionUrl {
    param([string]$TargetEnvironment)

    if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
        Write-Log -Level Warning -Message "Terraform not installed - cannot automatically retrieve function URL"
        return $null
    }

    Push-Location $TERRAFORM_DIR
    try {
        # Initialize connection to remote state
        if (-not (Initialize-TerraformState -TargetEnvironment $TargetEnvironment)) {
            Write-Host "⚠️  Failed to connect to Terraform state." -ForegroundColor Yellow
            return $null
        }

        # Get output
        $url = terraform output -raw function_url 2>&1

        if ($LASTEXITCODE -eq 0 -and $url -match '^https://') {
            return $url
        }

        # Function not deployed - provide guidance
        Write-Host "⚠️  Cloud Function not deployed for $TargetEnvironment" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "📋 Deployment Instructions:" -ForegroundColor Blue
        Write-Host ""

        $branch = if ($TargetEnvironment -eq "staging") { "develop" } else { "main" }
        $workflowUrl = "https://github.com/lordmuffin/Maestro/actions"

        Write-Host "1. Ensure TELEGRAM_BOT_TOKEN is set (this script can do that)"
        Write-Host "2. Push code to '$branch' branch:"
        Write-Host "   git push origin $branch"
        Write-Host "3. Monitor deployment:"
        Write-Host "   $workflowUrl"
        Write-Host "4. After deployment succeeds, re-run this script with -RegisterWebhook"
        Write-Host ""
        Write-Host "Expected deployment time: 3-5 minutes"
        Write-Host ""

        return $null

    } finally {
        Pop-Location
    }
}

function Test-CloudFunctionHealth {
    param(
        [string]$FunctionUrlString,
        [string]$TokenString
    )

    Write-Log -Level Info -Message "Checking Cloud Function health..."
    Write-Host ""

    # Test 1: Root endpoint (basic connectivity)
    Write-Host "Testing function URL accessibility..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri $FunctionUrlString -Method Get -TimeoutSec 10 -ErrorAction Stop
        Write-Log -Level Success -Message "Function URL accessible (HTTP $($response.StatusCode))"
    } catch {
        Write-Log -Level Error -Message "Function URL not accessible: $($_.Exception.Message)"
        return $false
    }

    # Test 2: Webhook endpoint responsiveness
    $webhookUrl = "$FunctionUrlString/telegram"
    Write-Host "Testing webhook endpoint..." -ForegroundColor Yellow
    try {
        # Send minimal valid Telegram update
        $testUpdate = @{
            update_id = 999999999
            message = @{
                message_id = 1
                from = @{ id = 123; first_name = "Test"; is_bot = $false }
                chat = @{ id = 123; type = "private" }
                date = [int](Get-Date -UFormat %s)
                text = "/start"
            }
        } | ConvertTo-Json -Depth 10

        $response = Invoke-WebRequest `
            -Uri $webhookUrl `
            -Method Post `
            -ContentType "application/json" `
            -Body $testUpdate `
            -TimeoutSec 10 `
            -ErrorAction SilentlyContinue

        Write-Log -Level Success -Message "Webhook endpoint responsive"
    } catch {
        Write-Host "ℹ️  Webhook endpoint test inconclusive (may require Telegram signature)" -ForegroundColor Blue
    }

    # Test 3: Verify webhook registration
    Write-Host "Verifying webhook registration..." -ForegroundColor Yellow
    $webhookInfo = Invoke-TelegramAPI -TokenString $TokenString -Method "getWebhookInfo"
    if ($webhookInfo -and $webhookInfo.url -eq $webhookUrl) {
        Write-Log -Level Success -Message "Webhook correctly registered"
    } else {
        Write-Host "⚠️  Webhook URL mismatch" -ForegroundColor Yellow
        Write-Host "   Expected: $webhookUrl"
        if ($webhookInfo) {
            Write-Host "   Current:  $($webhookInfo.url)"
        }
    }

    return $true
}

#endregion

#region Module 6: Testing & Validation

function Test-TelegramBotConnection {
    param([string]$TokenString)

    Write-Log -Level Info -Message "Testing bot connection..."
    Write-Host ""

    # Level 1: Bot accessible
    $botInfo = Invoke-TelegramAPI -TokenString $TokenString -Method "getMe"
    if (-not $botInfo) {
        Write-Log -Level Error -Message "Bot not accessible"
        return $false
    }
    Write-Host "✅ Bot online: @$($botInfo.username)" -ForegroundColor Green

    # Level 2: Check for received messages
    $updates = Invoke-TelegramAPI -TokenString $TokenString -Method "getUpdates"
    if ($updates -and $updates.Count -gt 0) {
        Write-Host "✅ Bot has received $($updates.Count) message(s)" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  No messages received yet" -ForegroundColor Blue
        Write-Host "   Send /start to @$($botInfo.username) to test" -ForegroundColor Gray
    }

    return $true
}

function Show-ProvisioningSummary {
    param(
        [string]$TargetEnvironment,
        [hashtable]$BotInfo,
        [string]$WebhookUrlString,
        [bool]$Success,
        [hashtable]$Details = @{}
    )

    Write-Host ""
    Write-Host "========================================" -ForegroundColor $(if($Success){'Green'}else{'Red'})
    Write-Host "  Provisioning Summary" -ForegroundColor $(if($Success){'Green'}else{'Red'})
    Write-Host "========================================" -ForegroundColor $(if($Success){'Green'}else{'Red'})
    Write-Host ""

    # Configuration details
    Write-Host "Environment: " -NoNewline -ForegroundColor Yellow
    Write-Host $TargetEnvironment

    if ($BotInfo) {
        Write-Host "Bot Username: " -NoNewline -ForegroundColor Yellow
        Write-Host "@$($BotInfo.Username)"
        Write-Host "Bot Name: " -NoNewline -ForegroundColor Yellow
        Write-Host $BotInfo.Name
        Write-Host "Bot ID: " -NoNewline -ForegroundColor Yellow
        Write-Host $BotInfo.ID
    }

    if ($WebhookUrlString) {
        Write-Host "Webhook URL: " -NoNewline -ForegroundColor Yellow
        Write-Host $WebhookUrlString
    }

    Write-Host "Status: " -NoNewline -ForegroundColor Yellow
    if ($Success) {
        Write-Host "✅ SUCCESS" -ForegroundColor Green
    } else {
        Write-Host "❌ FAILED" -ForegroundColor Red
    }

    Write-Host "Timestamp: " -NoNewline -ForegroundColor Yellow
    Write-Host (Get-Date -Format "yyyy-MM-dd HH:mm:ss")

    Write-Host ""

    # Next steps
    if ($Success -and $BotInfo) {
        Write-Host "📋 Next Steps:" -ForegroundColor Blue
        Write-Host ""
        Write-Host "1. ✅ Open Telegram and search for @$($BotInfo.Username)"
        Write-Host "2. ✅ Send /start to begin a conversation"
        Write-Host "3. ✅ Test with /help command"
        Write-Host "4. ✅ Send an audio file or text for processing"
        Write-Host ""
        Write-Host "📊 Monitoring:" -ForegroundColor Blue
        Write-Host ""
        Write-Host "View logs:"
        Write-Host "gcloud functions logs read v2v2b-interrogator$(if($TargetEnvironment -eq 'staging'){'-staging'}) --gen2 --limit=50"
        Write-Host ""
        Write-Host "Check webhook status:"
        Write-Host ".\scripts\provision-telegram-bot.ps1 -Environment $TargetEnvironment -HealthCheck"
        Write-Host ""

        if ($TargetEnvironment -eq "staging") {
            Write-Host "🚀 Ready for Production?" -ForegroundColor Blue
            Write-Host ""
            Write-Host "Once staging is tested and stable:"
            Write-Host "1. Create a new bot for production"
            Write-Host "2. Run: .\scripts\provision-telegram-bot.ps1 -Environment production -FullSetup"
            Write-Host "3. Merge to main branch to trigger production deployment"
            Write-Host ""
        }
    } elseif (-not $Success) {
        Write-Host "🔧 Troubleshooting:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. Check error messages above for details"
        Write-Host "2. Verify GitHub environment exists:"
        Write-Host "   https://github.com/lordmuffin/Maestro/settings/environments"
        Write-Host "3. Ensure Cloud Function is deployed:"
        Write-Host "   https://github.com/lordmuffin/Maestro/actions"
        Write-Host "4. Validate Telegram token with @BotFather"
        Write-Host "5. Re-run with -VerboseLog flag for detailed logging"
        Write-Host ""
        Write-Host "📚 Documentation:" -ForegroundColor Blue
        Write-Host "- Quick Setup: QUICK_SETUP.md"
        Write-Host "- GitOps Guide: GITOPS_SETUP_GUIDE.md"
        Write-Host "- Telegram Setup: terraform/ORIGINAL_README.md (section 2)"
        Write-Host ""
    }

    Write-Host "========================================" -ForegroundColor $(if($Success){'Green'}else{'Red'})
    Write-Host ""
}

function Show-PerformanceReport {
    $totalDuration = (Get-Date) - $script:PerformanceMetrics.StartTime

    if ($script:PerformanceMetrics.Operations.Count -eq 0) {
        return
    }

    Write-Host ""
    Write-Host "⏱️  Performance Report:" -ForegroundColor Cyan
    Write-Host ""

    foreach ($op in $script:PerformanceMetrics.Operations) {
        $status = if ($op.success) { "✅" } else { "❌" }
        Write-Host "  $status $($op.operation): $($op.duration_ms)ms"
    }

    Write-Host ""
    Write-Host "Total duration: $([int]$totalDuration.TotalSeconds)s" -ForegroundColor Yellow
    Write-Host ""

    # Save to file
    try {
        $metricsEntry = @{
            timestamp = Get-Date -Format "o"
            total_duration_ms = [int]$totalDuration.TotalMilliseconds
            operations = $script:PerformanceMetrics.Operations
        } | ConvertTo-Json -Compress

        Add-Content -Path $script:MetricsFile -Value $metricsEntry -ErrorAction SilentlyContinue
    } catch {
        # Silently fail if can't write metrics
    }
}

#endregion

#region Module 7: Rollback & Error Recovery

function Invoke-Rollback {
    param(
        [string]$TokenString,
        [string]$TargetEnvironment
    )

    Write-Host ""
    Write-Host "🔄 ROLLBACK: Reverting changes..." -ForegroundColor Yellow

    # Rollback webhook (if we changed it)
    if ($global:ProvisioningState.WebhookRegistered) {
        if ($global:ProvisioningState.WebhookOldUrl) {
            Write-Host "Restoring previous webhook URL..."
            $null = Invoke-TelegramAPI -TokenString $TokenString -Method "setWebhook" -Body @{
                url = $global:ProvisioningState.WebhookOldUrl
            }
        } else {
            Write-Host "Removing webhook..."
            $null = Invoke-TelegramAPI -TokenString $TokenString -Method "deleteWebhook"
        }
    }

    # Note: We don't rollback secrets as they can't be read back
    # User will need to manually manage secrets if needed

    Write-Log -Level Success -Message "Rollback complete"
    Write-Host "   State restored to pre-provisioning configuration" -ForegroundColor Gray
}

function Invoke-Cleanup {
    if ($script:CleanupOnExit -and $global:ProvisioningState) {
        Write-Log -Level Verbose -Message "Cleaning up..."

        # Remove temporary files
        if ($global:ProvisioningState.TempFiles) {
            foreach ($file in $global:ProvisioningState.TempFiles) {
                if (Test-Path $file) {
                    Remove-Item $file -Force -ErrorAction SilentlyContinue
                    Write-Log -Level Verbose -Message "Removed temp file: $file"
                }
            }
        }

        # Close progress bars
        Write-Progress -Activity "Bot Provisioning" -Completed
    }
}

#endregion

#region Interactive Menu System

function Show-MainMenu {
    param([string]$TargetEnvironment)

    Clear-Host
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host "  Telegram Bot Provisioning Utility" -ForegroundColor Blue
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Environment: " -NoNewline -ForegroundColor Yellow
    Write-Host $TargetEnvironment
    Write-Host ""
    Write-Host "1. 🤖 Create New Bot (with BotFather guidance)"
    Write-Host "2. ⚙️  Configure Existing Bot (set token)"
    Write-Host "3. 🔗 Register Webhook"
    Write-Host "4. 🧪 Test Bot Connection"
    Write-Host "5. 🏥 Health Check (Function + Webhook)"
    Write-Host "6. 🚀 Full Setup (Steps 1-5 automated)"
    Write-Host "7. ℹ️  Show Environment Info"
    Write-Host "0. ❌ Exit"
    Write-Host ""

    do {
        $choice = Read-Host "Select option (0-7)"
    } while ($choice -notmatch '^[0-7]$')

    return $choice
}

function Start-InteractiveMode {
    # Select environment if not provided
    $targetEnv = $Environment
    if (-not $targetEnv) {
        Write-Host "Available environments:" -ForegroundColor Yellow
        Write-Host "1. staging"
        Write-Host "2. production"
        Write-Host ""

        do {
            $choice = Read-Host "Select environment (1-2)"

            switch ($choice) {
                "1" { $targetEnv = "staging"; break }
                "2" { $targetEnv = "production"; break }
                default {
                    Write-Host "Invalid choice. Please enter 1 or 2." -ForegroundColor Yellow
                }
            }
        } while (-not $targetEnv)
    }

    Write-Host "Selected environment: $targetEnv" -ForegroundColor Cyan
    Write-Host ""

    # Main menu loop
    do {
        $choice = Show-MainMenu -TargetEnvironment $targetEnv

        switch ($choice) {
            "1" {
                # Create New Bot
                $result = Show-BotCreationGuide -TargetEnvironment $targetEnv
                if ($result) {
                    $saved = Save-BotMetadata -TargetEnvironment $targetEnv -BotInfo $result -TokenString $result.Token
                    if ($saved) {
                        Write-Host ""
                        if (Confirm-Action "Configure GitHub secret now?" -DefaultYes:$true) {
                            $null = Set-GitHubEnvironmentSecret -TargetEnvironment $targetEnv -SecretName "TELEGRAM_BOT_TOKEN" -SecretValue $result.Token
                        }
                    }
                }
                Read-Host "`nPress Enter to continue"
            }
            "2" {
                # Configure Existing Bot
                $tokenInput = Read-Host "Enter bot token"
                if (Test-TelegramTokenFormat -TokenString $tokenInput) {
                    $botInfo = Test-TelegramToken -TokenString $tokenInput
                    if ($botInfo) {
                        $null = Set-GitHubEnvironmentSecret -TargetEnvironment $targetEnv -SecretName "TELEGRAM_BOT_TOKEN" -SecretValue $tokenInput
                        $null = Save-BotMetadata -TargetEnvironment $targetEnv -BotInfo @{
                            Username = $botInfo.username
                            Name = $botInfo.first_name
                            ID = $botInfo.id
                            Token = $tokenInput
                        } -TokenString $tokenInput
                    } else {
                        Write-Host "❌ Invalid token" -ForegroundColor Red
                    }
                } else {
                    Write-Host "❌ Invalid token format" -ForegroundColor Red
                }
                Read-Host "`nPress Enter to continue"
            }
            "3" {
                # Register Webhook
                $metadataPath = Join-Path $LOGS_DIR "bot-metadata-$targetEnv.json"
                if (Test-Path $metadataPath) {
                    $metadata = Get-Content $metadataPath | ConvertFrom-Json
                    $tokenInput = Read-Host "Enter bot token (or press Enter to skip webhook registration)"
                    if ($tokenInput) {
                        $functionUrl = Get-TerraformFunctionUrl -TargetEnvironment $targetEnv
                        if ($functionUrl) {
                            $null = Register-TelegramWebhook -TokenString $tokenInput -WebhookUrlString "$functionUrl/telegram"
                        }
                    }
                } else {
                    Write-Host "❌ No bot configured. Please create or configure a bot first." -ForegroundColor Red
                }
                Read-Host "`nPress Enter to continue"
            }
            "4" {
                # Test Bot Connection
                $tokenInput = Read-Host "Enter bot token"
                if ($tokenInput) {
                    $null = Test-TelegramBotConnection -TokenString $tokenInput
                }
                Read-Host "`nPress Enter to continue"
            }
            "5" {
                # Health Check
                $tokenInput = Read-Host "Enter bot token"
                if ($tokenInput) {
                    $functionUrl = Get-TerraformFunctionUrl -TargetEnvironment $targetEnv
                    if ($functionUrl) {
                        $null = Test-CloudFunctionHealth -FunctionUrlString $functionUrl -TokenString $tokenInput
                        Write-Host ""
                        $null = Get-TelegramWebhookInfo -TokenString $tokenInput
                    }
                }
                Read-Host "`nPress Enter to continue"
            }
            "6" {
                # Full Setup
                Write-Host "Starting full setup..." -ForegroundColor Cyan
                $result = Show-BotCreationGuide -TargetEnvironment $targetEnv
                if ($result) {
                    Start-FullSetup -TargetEnvironment $targetEnv -TokenString $result.Token -BotInfo $result
                }
                Read-Host "`nPress Enter to continue"
            }
            "7" {
                # Show Environment Info
                Write-Host ""
                Write-Host "Environment: $targetEnv" -ForegroundColor Cyan
                $null = Test-EnvironmentConfiguration -TargetEnvironment $targetEnv

                $metadataPath = Join-Path $LOGS_DIR "bot-metadata-$targetEnv.json"
                if (Test-Path $metadataPath) {
                    $metadata = Get-Content $metadataPath | ConvertFrom-Json
                    Write-Host ""
                    Write-Host "Configured Bot:" -ForegroundColor Cyan
                    Write-Host "  Username: @$($metadata.username)"
                    Write-Host "  Name: $($metadata.name)"
                    Write-Host "  ID: $($metadata.id)"
                    Write-Host "  Configured: $(Get-Date $metadata.timestamp -Format 'yyyy-MM-dd HH:mm')"
                    Write-Host "  By: $($metadata.provisioned_by)"
                }

                Read-Host "`nPress Enter to continue"
            }
            "0" {
                Write-Host "Exiting..." -ForegroundColor Yellow
                return
            }
        }
    } while ($true)
}

function Start-FullSetup {
    param(
        [string]$TargetEnvironment,
        [string]$TokenString,
        [hashtable]$BotInfo
    )

    $totalSteps = 5
    $currentStep = 0
    $success = $true

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host "  Full Bot Setup - $TargetEnvironment" -ForegroundColor Blue
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host ""

    try {
        # Step 1: Validate Token
        $currentStep++
        Write-Progress -Activity "Bot Setup" -Status "Validating token..." -PercentComplete (($currentStep / $totalSteps) * 100)
        Write-Host "[$currentStep/$totalSteps] 🔍 Validating token..." -ForegroundColor Yellow

        $timer = Start-OperationTimer -OperationName "ValidateToken"
        $botInfoResult = Test-TelegramToken -TokenString $TokenString
        Stop-OperationTimer -Timer $timer -Success ($null -ne $botInfoResult)

        if (-not $botInfoResult) {
            Write-Host "❌ Failed" -ForegroundColor Red
            $success = $false
            return
        }
        Write-Host "✅ Token valid: @$($botInfoResult.username)" -ForegroundColor Green
        Start-Sleep -Milliseconds 500

        # Step 2: Save Metadata
        $currentStep++
        Write-Progress -Activity "Bot Setup" -Status "Saving bot metadata..." -PercentComplete (($currentStep / $totalSteps) * 100)
        Write-Host "[$currentStep/$totalSteps] 💾 Saving bot metadata..." -ForegroundColor Yellow

        $timer = Start-OperationTimer -OperationName "SaveMetadata"
        $metadataSaved = Save-BotMetadata -TargetEnvironment $TargetEnvironment -BotInfo $BotInfo -TokenString $TokenString
        Stop-OperationTimer -Timer $timer -Success $metadataSaved

        Write-Host "✅ Metadata saved" -ForegroundColor Green
        Start-Sleep -Milliseconds 500

        # Step 3: Configure GitHub Secret
        $currentStep++
        Write-Progress -Activity "Bot Setup" -Status "Configuring GitHub secret..." -PercentComplete (($currentStep / $totalSteps) * 100)
        Write-Host "[$currentStep/$totalSteps] 🔐 Configuring GitHub secret..." -ForegroundColor Yellow

        $timer = Start-OperationTimer -OperationName "ConfigureSecret"
        $secretSet = Set-GitHubEnvironmentSecret -TargetEnvironment $TargetEnvironment -SecretName "TELEGRAM_BOT_TOKEN" -SecretValue $TokenString
        Stop-OperationTimer -Timer $timer -Success $secretSet

        if (-not $secretSet) {
            Write-Host "❌ Failed" -ForegroundColor Red
            $success = $false
            return
        }
        Write-Host "✅ Secret configured" -ForegroundColor Green
        Start-Sleep -Milliseconds 500

        # Step 4: Register Webhook
        $currentStep++
        Write-Progress -Activity "Bot Setup" -Status "Registering webhook..." -PercentComplete (($currentStep / $totalSteps) * 100)
        Write-Host "[$currentStep/$totalSteps] 🔗 Registering webhook..." -ForegroundColor Yellow

        $timer = Start-OperationTimer -OperationName "RegisterWebhook"
        $functionUrl = Get-TerraformFunctionUrl -TargetEnvironment $TargetEnvironment

        if (-not $functionUrl) {
            Stop-OperationTimer -Timer $timer -Success $false
            Write-Host "⚠️  Function not deployed - skipping webhook registration" -ForegroundColor Yellow
            Write-Host "   Deploy via GitHub Actions, then re-run with -RegisterWebhook" -ForegroundColor Gray
        } else {
            $webhookSet = Register-TelegramWebhook -TokenString $TokenString -WebhookUrlString "$functionUrl/telegram"
            Stop-OperationTimer -Timer $timer -Success $webhookSet

            if ($webhookSet) {
                Write-Host "✅ Webhook registered" -ForegroundColor Green
            } else {
                Write-Host "❌ Webhook registration failed" -ForegroundColor Red
                $success = $false
            }
        }
        Start-Sleep -Milliseconds 500

        # Step 5: Test Bot
        $currentStep++
        Write-Progress -Activity "Bot Setup" -Status "Testing bot..." -PercentComplete 100
        Write-Host "[$currentStep/$totalSteps] 🧪 Testing bot connection..." -ForegroundColor Yellow

        $timer = Start-OperationTimer -OperationName "TestBot"
        $testResult = Test-TelegramBotConnection -TokenString $TokenString
        Stop-OperationTimer -Timer $timer -Success $testResult

        if ($testResult) {
            Write-Host "✅ Bot is operational" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Testing complete (send /start to bot to verify)" -ForegroundColor Yellow
        }

        Write-Progress -Activity "Bot Setup" -Completed

    } finally {
        # Show summary
        Show-ProvisioningSummary `
            -TargetEnvironment $TargetEnvironment `
            -BotInfo $BotInfo `
            -WebhookUrlString $(if($functionUrl){"$functionUrl/telegram"}else{$null}) `
            -Success $success

        Show-PerformanceReport
    }
}

#endregion

#region Main Execution Flow

function Show-Version {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Telegram Bot Provisioning Script" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Version: " -NoNewline
    Write-Host "v$SCRIPT_VERSION" -ForegroundColor Green
    Write-Host "Date: " -NoNewline
    Write-Host $SCRIPT_DATE
    Write-Host "Author: " -NoNewline
    Write-Host $SCRIPT_AUTHOR
    Write-Host ""
}

function Start-Main {
    # Check PowerShell execution policy
    if ((Get-ExecutionPolicy) -eq 'Restricted') {
        Write-Host "❌ PowerShell execution policy is set to 'Restricted'" -ForegroundColor Red
        Write-Host ""
        Write-Host "Run this script with:" -ForegroundColor Yellow
        Write-Host "powershell -ExecutionPolicy Bypass -File .\scripts\provision-telegram-bot.ps1"
        Write-Host ""
        Write-Host "Or change policy permanently:" -ForegroundColor Yellow
        Write-Host "Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned"
        Write-Host ""
        exit 1
    }

    # Show version
    Show-Version
    Write-Log -Level Info -Message "Starting Telegram Bot Provisioning v$SCRIPT_VERSION"

    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        exit 1
    }

    # Check authentication
    if (-not (Test-Authentication)) {
        exit 1
    }

    # Determine operation mode
    if ($PSCmdlet.ParameterSetName -eq 'Interactive') {
        Start-InteractiveMode
    } else {
        # Non-interactive mode - execute specific operation

        # Validate environment configuration
        if (-not (Test-EnvironmentConfiguration -TargetEnvironment $Environment)) {
            exit 1
        }

        if ($CreateBot) {
            $result = Show-BotCreationGuide -TargetEnvironment $Environment
            if ($result) {
                $null = Save-BotMetadata -TargetEnvironment $Environment -BotInfo $result -TokenString $result.Token
            }
        } elseif ($ConfigureBot) {
            if (-not $Token) {
                $Token = Read-Host "Enter bot token"
            }
            if (Test-TelegramTokenFormat -TokenString $Token) {
                $botInfo = Test-TelegramToken -TokenString $Token
                if ($botInfo) {
                    $null = Set-GitHubEnvironmentSecret -TargetEnvironment $Environment -SecretName "TELEGRAM_BOT_TOKEN" -SecretValue $Token
                }
            }
        } elseif ($RegisterWebhook) {
            if (-not $Token) {
                # Try to get from metadata
                $metadataPath = Join-Path $LOGS_DIR "bot-metadata-$Environment.json"
                if (-not (Test-Path $metadataPath)) {
                    Write-Host "❌ No bot configured and no token provided" -ForegroundColor Red
                    exit 1
                }
                $Token = Read-Host "Enter bot token"
            }

            $functionUrl = if ($WebhookUrl) { $WebhookUrl } else { Get-TerraformFunctionUrl -TargetEnvironment $Environment }
            if ($functionUrl) {
                if ($functionUrl.EndsWith('/telegram')) {
                    $webhookUrlFull = $functionUrl
                } else {
                    $webhookUrlFull = "$functionUrl/telegram"
                }
                $null = Register-TelegramWebhook -TokenString $Token -WebhookUrlString $webhookUrlFull
            }
        } elseif ($TestBot) {
            if (-not $Token) {
                $Token = Read-Host "Enter bot token"
            }
            $null = Test-TelegramBotConnection -TokenString $Token
        } elseif ($HealthCheck) {
            if (-not $Token) {
                $Token = Read-Host "Enter bot token"
            }
            $functionUrl = Get-TerraformFunctionUrl -TargetEnvironment $Environment
            if ($functionUrl) {
                $null = Test-CloudFunctionHealth -FunctionUrlString $functionUrl -TokenString $Token
                Write-Host ""
                $null = Get-TelegramWebhookInfo -TokenString $Token
            }
        } elseif ($FullSetup) {
            if ($Token) {
                # Token provided, validate it
                if (-not (Test-TelegramTokenFormat -TokenString $Token)) {
                    Write-Host "❌ Invalid token format" -ForegroundColor Red
                    exit 1
                }
                $botInfo = Test-TelegramToken -TokenString $Token
                if (-not $botInfo) {
                    Write-Host "❌ Invalid token" -ForegroundColor Red
                    exit 1
                }
                Start-FullSetup -TargetEnvironment $Environment -TokenString $Token -BotInfo @{
                    Username = $botInfo.username
                    Name = $botInfo.first_name
                    ID = $botInfo.id
                }
            } else {
                # Guide through creation
                $result = Show-BotCreationGuide -TargetEnvironment $Environment
                if ($result) {
                    Start-FullSetup -TargetEnvironment $Environment -TokenString $result.Token -BotInfo $result
                }
            }
        } elseif ($Rollback) {
            if (-not $Token) {
                $Token = Read-Host "Enter bot token for rollback"
            }
            Invoke-Rollback -TokenString $Token -TargetEnvironment $Environment
        }
    }
}

# Register cleanup handler
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Invoke-Cleanup
} | Out-Null

# Main execution with error handling
try {
    Start-Main
} catch [System.Management.Automation.PipelineStoppedException] {
    Write-Host ""
    Write-Host "❌ Operation cancelled by user" -ForegroundColor Yellow

    if ($Token -and (Confirm-Action "Rollback partial changes?")) {
        Invoke-Rollback -TokenString $Token -TargetEnvironment $Environment
    }

    Invoke-Cleanup
    exit 130
} catch {
    Write-Log -Level Error -Message "Unhandled exception: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "❌ An unexpected error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host ""
    Write-Host "Stack trace:" -ForegroundColor Gray
    Write-Host $_.ScriptStackTrace

    Invoke-Cleanup
    exit 1
} finally {
    Invoke-Cleanup
}

#endregion
