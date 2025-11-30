# Azure Deployment Setup Guide

This guide describes how to set up the Azure infrastructure for the V2V2B Interrogator bot using OpenTofu.

## Prerequisites

1.  **Azure CLI**: [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
2.  **OpenTofu**: [Install OpenTofu](https://opentofu.org/docs/intro/install/)
3.  **PowerShell**: Required to run the bootstrap script.

## 1. Bootstrap Azure Backend

To manage Terraform state securely, we use an Azure Storage Account. A helper script is provided to create the necessary resources.

1.  Open a PowerShell terminal.
2.  Login to Azure:
    ```powershell
    Connect-AzAccount
    ```
3.  Run the bootstrap script:
    ```powershell
    ./scripts/bootstrap_azure.ps1 -Location "eastus" -ResourceGroupName "rg-maestro-tfstate"
    ```
    *Note: If you don't provide a storage account name, one will be generated for you.*

4.  **Save the Output!** The script will output values for `Resource Group Name`, `Storage Account Name`, `Container Name`, and `Access Key`. You will need these for the next steps.

## 2. Configure GitHub Secrets

Navigate to your GitHub repository -> Settings -> Secrets and variables -> Actions -> New repository secret.

Add the following secrets:

### Authentication (Service Principal)
You need an Azure Service Principal for GitHub Actions to deploy resources.
Run this command to create one:
```bash
az ad sp create-for-rbac --name "github-action-maestro" --role Contributor --scopes /subscriptions/<SUBSCRIPTION_ID> --sdk-auth
```
Extract the values from the JSON output and map them to these secrets:
-   `AZURE_CLIENT_ID`: `clientId`
-   `AZURE_CLIENT_SECRET`: `clientSecret`
-   `AZURE_TENANT_ID`: `tenantId`
-   `AZURE_SUBSCRIPTION_ID`: `subscriptionId`

### Terraform Backend Configuration
Use the values from the bootstrap script:
-   `TF_BACKEND_RESOURCE_GROUP`: The resource group created by the script.
-   `TF_BACKEND_STORAGE_ACCOUNT`: The storage account name.
-   `TF_BACKEND_CONTAINER`: The container name (default `tfstate`).

### Application Secrets
-   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token.
-   `GCP_PROJECT_ID`: (Optional) If integrating with existing GCP resources.

## 3. Local Development (Optional)

To run OpenTofu locally:

1.  Navigate to `terraform/azure`.
2.  Initialize OpenTofu with the backend configuration:
    ```bash
    tofu init \
      -backend-config="resource_group_name=<RG_NAME>" \
      -backend-config="storage_account_name=<SA_NAME>" \
      -backend-config="container_name=<CONTAINER_NAME>" \
      -backend-config="key=dev.terraform.tfstate"
    ```
3.  Plan and Apply:
    ```bash
    tofu plan
    tofu apply
    ```
