# Maestro OpenTofu Infrastructure (Azure)

This directory contains the OpenTofu (Terraform) configuration for deploying the Maestro "Interrogator" bot to **Microsoft Azure**.

## Architecture

The infrastructure is deployed to Azure and consists of the following resources:

*   **Azure Function App (Linux)**: Hosts the Python application (V2V2B).
*   **Azure Cosmos DB (SQL API)**: Stores conversation history and state (replacing Firestore).
*   **Azure Storage Account**:
    *   Used by the Function App for internal storage.
    *   Stores `terraform.tfstate` (in the `tfstate` container).
*   **Application Insights**: Provides monitoring and logging.

## Prerequisites

1.  **Azure CLI**: Ensure `az` CLI is installed and you are logged in (`az login`).
2.  **OpenTofu**: Install OpenTofu (v1.6+).
3.  **GitHub Secrets**: The following secrets must be configured in the GitHub repository for CI/CD:
    *   `AZURE_CLIENT_ID`
    *   `AZURE_TENANT_ID`
    *   `AZURE_SUBSCRIPTION_ID`
    *   `TF_STATE_RESOURCE_GROUP_NAME` (Variable)
    *   `TF_STATE_STORAGE_ACCOUNT_NAME` (Variable)
    *   `GH_TOKEN_MAESTRO`, `GH_TOKEN_BEYOND`: GitHub Personal Access Tokens.
    *   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token.

## Local Development

1.  **Initialize**:
    ```bash
    tofu init
    ```
    *Note: You may need to provide backend config matching your Azure Storage account.*

2.  **Select Workspace**:
    ```bash
    tofu workspace select staging  # or production
    ```

3.  **Plan**:
    ```bash
    tofu plan -var-file="environments/staging.tfvars"
    ```

4.  **Apply**:
    ```bash
    tofu apply -var-file="environments/staging.tfvars"
    ```

## Secrets Management

Sensitive values (tokens, keys) are managed via GitHub Secrets and injected as environment variables or `terraform.tfvars`.

## Migration from GCP

This configuration replaces the previous Google Cloud Platform setup.
- **Compute**: Cloud Run/Functions -> Azure Functions
- **Database**: Firestore -> Azure Cosmos DB
- **Storage**: GCS -> Azure Storage

## Repository Structure

*   `main.tf`: Core resource definitions (Resource Group, Function, Cosmos DB).
*   `variables.tf`: Input variable definitions.
*   `outputs.tf`: Output values (Function URL, etc.).
*   `backend.tf`: Azure Backend configuration.
*   `environments/`: Environment-specific variable files (`staging.tfvars`, `production.tfvars`).
