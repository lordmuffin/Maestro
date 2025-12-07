<#
.SYNOPSIS
    Initializes Azure resources and permissions for Maestro GitHub Actions workflows.

.DESCRIPTION
    This script automates the setup of:
    1. Azure App Registration & Service Principal for GitHub Actions.
    2. Federated Credentials (OIDC) for 'staging', 'production' environments and 'terraform-plan' (PRs).
    3. Resource Group for Terraform State.
    4. Storage Account and Container for Terraform State.
    5. Contributor role assignment for the Service Principal.
    6. GitHub Secrets output (and optional auto-setting).

.NOTES
    Prerequisites:
    - Azure CLI installed and logged in (az login) with Owner or User Access Administrator permissions.
    - GitHub CLI (gh) installed (optional, for setting secrets automatically).
#>

param(
    [string]$SubscriptionId,
    [string]$AppName = "sp-maestro-github",
    [string]$ResourceGroupName = "rg-terraform-state",
    [string]$Location = "eastus",
    [string]$RepoOwner = "lordmuffin",
    [string]$RepoName = "Maestro",
    [switch]$SetGitHubSecrets
)

$ErrorActionPreference = "Stop"

Write-Host "Running with: RepoOwner=$RepoOwner, RepoName=$RepoName, ResourceGroup=$ResourceGroupName" -ForegroundColor Cyan

# --- Helper Functions ---
function Write-Header {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "SUCCESS: $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "WARNING: $Message" -ForegroundColor Yellow
}

function Write-ErrorCustom {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
}

# --- Pre-checks ---
Write-Header "Checking Prerequisites"

if (-not (Get-Command "az" -ErrorAction SilentlyContinue)) {
    Write-ErrorCustom "Azure CLI (az) is not installed."
    exit 1
}

# Check login status
try {
    $currentAccount = az account show --output json | ConvertFrom-Json
    Write-Host "Logged in as: $($currentAccount.user.name)" -ForegroundColor Gray
    
    if ([string]::IsNullOrEmpty($SubscriptionId)) {
        $SubscriptionId = $currentAccount.id
    }
}
catch {
    Write-ErrorCustom "Not logged in to Azure. Please run 'az login' first."
    exit 1
}

Write-Host "Using Subscription ID: $SubscriptionId" -ForegroundColor Gray
az account set --subscription $SubscriptionId

# --- 1. Resource Group for State ---
Write-Header "Setting up Terraform State Resources"

# Create Resource Group
$rgExists = az group show --name $ResourceGroupName --output json 2>$null
if (-not $rgExists) {
    Write-Host "Creating Resource Group '$ResourceGroupName'..."
    az group create --name $ResourceGroupName --location $Location | Out-Null
    Write-Success "Resource Group created."
}
else {
    Write-Host "Resource Group '$ResourceGroupName' already exists." -ForegroundColor Gray
}

# Create Storage Account (Randomized name if checks logic needed, but for idempotency we try to stick to a convention or prompt)
# For simplicity/automation, we'll generate a consistent hash-based name or use a variable.
# Let's try to find an existing one or create a new one with a unique suffix.
$saPrefix = "stmaestrotfstate"
# Simple way to get a unique suffix based on sub ID to avoid global conflicts if re-used, 
# but for this specific user/repo, a fixed name might be better if they want to re-run.
# Let's check if we can find one in the RG.
$existingSas = az storage account list --resource-group $ResourceGroupName --query "[?starts_with(name, '$saPrefix')].name" --output tsv
if ($existingSas) {
    $StorageAccountName = $existingSas | Select-Object -First 1
    Write-Host "Found existing storage account: $StorageAccountName" -ForegroundColor Gray
}
else {
    # Generate unique name
    $uniqueSuffix = $SubscriptionId.Substring(0, 6)
    $StorageAccountName = "$saPrefix$uniqueSuffix"
    Write-Host "Creating Storage Account '$StorageAccountName'..."
    az storage account create --name $StorageAccountName --resource-group $ResourceGroupName --location $Location --sku Standard_LRS --encryption-services blob | Out-Null
    Write-Success "Storage Account created."
}

# Create Container
$ContainerName = "tfstate"
$containerExists = az storage container exists --name $ContainerName --account-name $StorageAccountName --auth-mode login --output json | ConvertFrom-Json
if (-not $containerExists.exists) {
    Write-Host "Creating Blob Container '$ContainerName'..."
    az storage container create --name $ContainerName --account-name $StorageAccountName --auth-mode login | Out-Null
    Write-Success "Blob Container created."
}
else {
    Write-Host "Blob Container '$ContainerName' already exists." -ForegroundColor Gray
}

# --- 2. Service Principal & App Registration ---
Write-Header "Setting up Service Principal & OIDC"

$spJson = az ad sp list --display-name $AppName --output json | ConvertFrom-Json
if ($spJson) {
    $ClientId = $spJson[0].appId
    $ObjectId = $spJson[0].id
    Write-Host "Found existing App Registration '$AppName' (ClientID: $ClientId)" -ForegroundColor Gray
}
else {
    Write-Host "Creating App Registration '$AppName'..."
    $spCreated = az ad sp create-for-rbac --name $AppName --role "Contributor" --scopes "/subscriptions/$SubscriptionId" --output json | ConvertFrom-Json
    $ClientId = $spCreated.appId
    # Need to get the Object ID (Enterprise Application object ID, strictly speaking for OIDC we need the App object ID for federated creds)
    # Actually, `create-for-rbac` creates the SP. 
    # We need the Application Object ID (not the SP ID) to configure federated credentials on the App Registration.
    # Wait a bit for propagation
    Start-Sleep -Seconds 5
}

# Retrieve App Object ID (needed for federated credentials)
$appObjectId = az ad app list --display-name $AppName --query "[0].id" --output tsv

if (-not $appObjectId) {
    Write-ErrorCustom "Could not retrieve App Object ID. Azure propagation might be slow. Try running again."
    exit 1
}

# --- 3. Federated Credentials (OIDC) ---
# We need to add federated credentials for each environment/scenario
$scenarios = @(
    @{ Name = "oidc-staging"; Subject = "repo:${RepoOwner}/${RepoName}:environment:staging" },
    @{ Name = "oidc-production"; Subject = "repo:${RepoOwner}/${RepoName}:environment:production" },
    @{ Name = "oidc-pull-request"; Subject = "repo:${RepoOwner}/${RepoName}:environment:terraform-plan" },
    @{ Name = "oidc-main-branch"; Subject = "repo:${RepoOwner}/${RepoName}:ref:refs/heads/main" }
)

foreach ($s in $scenarios) {
    $fName = $s.Name
    $fSubject = $s.Subject
    
    # Check if exists
    $creds = az ad app federated-credential list --id $appObjectId --query "[?name=='$fName']" --output json | ConvertFrom-Json
    
    if ($creds) {
        # Check if subject matches
        $existingSubject = $creds[0].subject
        if ($existingSubject -ne $fSubject) {
            Write-Warning "Credential '$fName' exists but subject mismatch.`nExpected: $fSubject`nActual:   $existingSubject`nRecreating..."
            az ad app federated-credential delete --id $appObjectId --federated-credential-id $fName | Out-Null
            $creds = $null # Force recreate
        }
        else {
            Write-Host "Federated Credential '$fName' already exists and is correct." -ForegroundColor Gray
        }
    }
    
    if (-not $creds) {
        Write-Host "Creating Federated Credential '$fName' ($fSubject)..."
        $params = @{
            name        = $fName
            issuer      = "https://token.actions.githubusercontent.com"
            subject     = $fSubject
            description = "GitHub Actions OIDC for $fName"
            audiences   = @("api://AzureADTokenExchange")
        }
        
        # Construct JSON for parameters to avoid parsing issues
        $jsonParams = $params | ConvertTo-Json
        $tempFile = [System.IO.Path]::GetTempFileName()
        $jsonParams | Set-Content $tempFile
        
        az ad app federated-credential create --id $appObjectId --parameters $tempFile | Out-Null
        Remove-Item $tempFile
        Write-Success "Credential '$fName' created."
    }
}

# --- 4. Role Assignment ---
# Ensure Contributor on Subscription (created by create-for-rbac, but strictly checking/fixing if we used existing SP)
# Getting SP Object ID (Principal ID)
$spObjectId = az ad sp list --filter "appId eq '$ClientId'" --query "[0].id" --output tsv

Write-Host "Ensuring Contributor role on Subscription..."
$roleAssigned = az role assignment list --assignee $spObjectId --role "Contributor" --scope "/subscriptions/$SubscriptionId" --output json | ConvertFrom-Json
if (-not $roleAssigned) {
    az role assignment create --assignee $spObjectId --role "Contributor" --scope "/subscriptions/$SubscriptionId" | Out-Null
    Write-Success "Contributor role assigned."
}
else {
    Write-Host "Contributor role already assigned." -ForegroundColor Gray
}


# --- 5. Outputs & github logic ---
$TenantId = az account show --query "tenantId" --output tsv

Write-Header "Setup Complete"
Write-Host "Please ensure the following secrets/vars are set in your GitHub Repository:"

$secrets = @{
    "AZURE_CLIENT_ID"       = $ClientId
    "AZURE_TENANT_ID"       = $TenantId
    "AZURE_SUBSCRIPTION_ID" = $SubscriptionId
}

$vars = @{
    "TF_STATE_RESOURCE_GROUP_NAME"  = $ResourceGroupName
    "TF_STATE_STORAGE_ACCOUNT_NAME" = $StorageAccountName
}

# Display
Write-Host "`n--- Secrets (Sensitive) ---" -ForegroundColor Magenta
foreach ($k in $secrets.Keys) {
    Write-Host "$k = $($secrets[$k])"
}

Write-Host "`n--- Variables (Non-sensitive) ---" -ForegroundColor Blue
foreach ($k in $vars.Keys) {
    Write-Host "$k = $($vars[$k])"
}

if ($SetGitHubSecrets) {
    if (Get-Command "gh" -ErrorAction SilentlyContinue) {
        Write-Header "Automatically Setting GitHub Secrets"
        
        # Set Secrets
        foreach ($k in $secrets.Keys) {
            Write-Host "Setting secret $k..."
            gh secret set $k --body "$($secrets[$k])"
        }
        
        # Set Vars
        foreach ($k in $vars.Keys) {
            Write-Host "Setting variable $k..."
            gh variable set $k --body "$($vars[$k])"
        }
        
        Write-Success "GitHub secrets and variables updated."
    }
    else {
        Write-Warning "Switch -SetGitHubSecrets was passed, but 'gh' CLI is not found. Skipping auto-setup."
    }
}
else {
    Write-Host "`nRun with -SetGitHubSecrets to automatically set these using 'gh' CLI." -ForegroundColor Cyan
}
