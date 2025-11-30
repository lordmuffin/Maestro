<#
.SYNOPSIS
    Bootstraps the Azure infrastructure for Terraform state management.
.DESCRIPTION
    This script creates a Resource Group, Storage Account, and Blob Container
    specifically for storing Terraform state files. It outputs the necessary
    configuration details to be used in the Terraform backend setup.
.PARAMETER ResourceGroupName
    The name of the Resource Group to create. Defaults to 'rg-maestro-terraform-state'.
.PARAMETER Location
    The Azure region to deploy to. Defaults to 'eastus'.
.PARAMETER StorageAccountName
    The name of the Storage Account. Must be globally unique.
    If not provided, a random name will be generated.
.PARAMETER ContainerName
    The name of the Blob Container. Defaults to 'tfstate'.
.EXAMPLE
    .\bootstrap_azure.ps1 -Location 'westus'
#>

param(
    [string]$ResourceGroupName = "rg-maestro-terraform-state",
    [string]$Location = "eastus",
    [string]$StorageAccountName,
    [string]$ContainerName = "tfstate"
)

# Check if logged in to Azure
try {
    $account = Get-AzContext
    if ($null -eq $account) {
        Write-Error "Please login to Azure using 'Connect-AzAccount' before running this script."
        exit 1
    }
    Write-Host "Connected to Azure subscription: $($account.Subscription.Name) ($($account.Subscription.Id))" -ForegroundColor Green
}
catch {
    Write-Error "Error checking Azure context. Please ensure Azure PowerShell module is installed and you are logged in."
    exit 1
}

# Generate random storage account name if not provided
if ([string]::IsNullOrEmpty($StorageAccountName)) {
    $randomSuffix = -join ((97..122) | Get-Random -Count 6 | ForEach-Object {[char]$_})
    $StorageAccountName = "stmaestrotf$randomSuffix"
    Write-Host "No StorageAccountName provided. Generated: $StorageAccountName" -ForegroundColor Cyan
}

# Create Resource Group
Write-Host "Creating Resource Group '$ResourceGroupName' in '$Location'..."
try {
    $rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
    if ($null -eq $rg) {
        New-AzResourceGroup -Name $ResourceGroupName -Location $Location -Force | Out-Null
        Write-Host "Resource Group created successfully." -ForegroundColor Green
    } else {
        Write-Host "Resource Group already exists." -ForegroundColor Yellow
    }
}
catch {
    Write-Error "Failed to create Resource Group: $_"
    exit 1
}

# Create Storage Account
Write-Host "Creating Storage Account '$StorageAccountName'..."
try {
    $storage = Get-AzStorageAccount -ResourceGroupName $ResourceGroupName -Name $StorageAccountName -ErrorAction SilentlyContinue
    if ($null -eq $storage) {
        $storage = New-AzStorageAccount -ResourceGroupName $ResourceGroupName `
            -Name $StorageAccountName `
            -SkuName Standard_LRS `
            -Location $Location `
            -Kind StorageV2 `
            -EnableHttpsTrafficOnly $true `
            -AllowBlobPublicAccess $false `
            -Force
        Write-Host "Storage Account created successfully." -ForegroundColor Green
    } else {
        Write-Host "Storage Account already exists." -ForegroundColor Yellow
    }
}
catch {
    Write-Error "Failed to create Storage Account: $_"
    exit 1
}

# Get Storage Account Key
$ctx = $storage.Context

# Create Container
Write-Host "Creating Blob Container '$ContainerName'..."
try {
    $container = Get-AzStorageContainer -Context $ctx -Name $ContainerName -ErrorAction SilentlyContinue
    if ($null -eq $container) {
        New-AzStorageContainer -Context $ctx -Name $ContainerName -Permission Off | Out-Null
        Write-Host "Container created successfully." -ForegroundColor Green
    } else {
        Write-Host "Container already exists." -ForegroundColor Yellow
    }
}
catch {
    Write-Error "Failed to create Container: $_"
    exit 1
}

# Retrieve Access Key
$keys = Get-AzStorageAccountKey -ResourceGroupName $ResourceGroupName -Name $StorageAccountName
$accountKey = $keys[0].Value

Write-Host "`n=== Terraform Backend Configuration Info ===" -ForegroundColor Magenta
Write-Host "Resource Group Name:  $ResourceGroupName"
Write-Host "Storage Account Name: $StorageAccountName"
Write-Host "Container Name:       $ContainerName"
Write-Host "Access Key:           $accountKey"
Write-Host "==========================================`n"

Write-Host "You can now configure your backend.tf or use these values in your GitHub Secrets/Environment Variables."
Write-Host "For GitHub Actions, set the following secrets:"
Write-Host "ARM_ACCESS_KEY: <The Access Key printed above>"
Write-Host "TF_VAR_backend_resource_group_name: $ResourceGroupName"
Write-Host "TF_VAR_backend_storage_account_name: $StorageAccountName"
Write-Host "TF_VAR_backend_container_name: $ContainerName"
