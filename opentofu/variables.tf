variable "azure_subscription_id" {
  description = "The Azure Subscription ID"
  type        = string
}

variable "location" {
  description = "The Azure region for resource deployment"
  type        = string
  default     = "eastus2"
}

variable "service_plan_sku" {
  description = "The SKU for the App Service Plan (e.g., B1, Y1 for consumption)"
  type        = string
  default     = "Y1" # Consumption plan
}

variable "environment" {
  description = "Environment name (e.g., staging, production)"
  type        = string
  default     = "staging"
}

variable "resource_group_name" {
  description = "Name of the resource group (optional, can be auto-generated)"
  type        = string
  default     = ""
}

variable "function_name" {
  description = "Name of the Azure Function App"
  type        = string
  default     = "v2v2b-interrogator"
}

variable "github_tokens" {
  description = "Map of GitHub tokens for each repository (key: repo label, value: token)"
  type        = map(string)
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token"
  type        = string
  sensitive   = true
}

variable "repos_config_file" {
  description = "Path to repository configuration file (JSON or YAML)"
  type        = string
  default     = "repos.json"
}

# Cosmos DB variables (formerly Firestore)
variable "cosmos_db_name" {
  description = "Name of the Cosmos DB account"
  type        = string
  default     = "" # If empty, will generate one
}

# Storage Account for Function
variable "storage_account_name" {
  description = "Name of the storage account for the function app"
  type        = string
  default     = "" # If empty, will generate one
}

# App Service Plan


# Whitelist variable kept from GCP config
variable "logs_whitelist" {
  description = "Comma-separated list of users/IDs whitelisted for logs"
  type        = string
  default     = ""
}

# Drive folder IDs kept consistent (application vars)
variable "google_drive_folder_id" {
  type    = string
  default = ""
}
variable "obsidian_drive_folder_id" {
  type    = string
  default = ""
}
variable "kanban_folder_id" {
  type    = string
  default = ""
}
variable "drive_poll_interval" {
  type    = number
  default = 300
}
variable "beyond_repo_name" {
  type    = string
  default = "lordmuffin/beyond"
}
