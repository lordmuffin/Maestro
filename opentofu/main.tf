terraform {
  required_version = ">= 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id = var.azure_subscription_id
}

# Random string for unique naming if needed
resource "random_string" "unique_id" {
  length  = 8
  special = false
  upper   = false
}

locals {
  # Generate names if not provided
  rg_name     = var.resource_group_name != "" ? var.resource_group_name : "rg-${var.function_name}-${var.environment}-${random_string.unique_id.result}"
  
  # Storage Account name must be max 24 chars, lowercase, alphanumeric.
  # We take the function name (stripped of hyphens), truncate to 15 chars, and append 8 random chars. 23 chars max.
  sa_name_base = substr(replace(var.function_name, "-", ""), 0, 15)
  sa_name      = var.storage_account_name != "" ? var.storage_account_name : "st${local.sa_name_base}${random_string.unique_id.result}"

  # Cosmos DB name must be max 44 chars.
  # We construct a base name and ensure it fits.
  # "cosmos-" (7) + func_name (truncated) + "-" + env + "-" + random (8)
  # Limit base func name to ensure fit.
  cosmos_name = var.cosmos_db_name != "" ? var.cosmos_db_name : "cosmos-${substr(var.function_name, 0, 18)}-${var.environment}-${random_string.unique_id.result}"

  # Function App name needs to be globally unique
  func_app_name = "${var.function_name}-${var.environment}-${random_string.unique_id.result}"
}

# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = local.rg_name
  location = var.location
  tags = {
    Environment = var.environment
    ManagedBy   = "OpenTofu"
  }
}

# Storage Account (Required for Function App)
resource "azurerm_storage_account" "sa" {
  name                     = local.sa_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  depends_on               = [azurerm_resource_group.rg]
}

# Application Insights (for monitoring)
resource "azurerm_application_insights" "app_insights" {
  name                = "api-${var.function_name}-${var.environment}-${random_string.unique_id.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
}

# App Service Plan (Consumption)
resource "azurerm_service_plan" "asp" {
  name                = "asp-${var.function_name}-${var.environment}-${random_string.unique_id.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = var.service_plan_sku
}

# Packaging the function code
data "archive_file" "function_source" {
  type        = "zip"
  output_path = "${path.module}/.terraform/function-source.zip"

  source {
    content  = file("${path.module}/../V2V2B/function_app.py")
    filename = "function_app.py"
  }
  source {
    content  = file("${path.module}/../V2V2B/requirements.txt")
    filename = "requirements.txt"
  }
  source {
    content  = file("${path.module}/../V2V2B/${var.repos_config_file}")
    filename = "repos.json"
  }

  # Include Prompts
  source {
    content  = file("${path.module}/../prompts/telegram_chat_prompt.md")
    filename = "prompts/telegram_chat_prompt.md"
  }
  source {
    content  = file("${path.module}/../prompts/multimodal_analysis_prompt.md")
    filename = "prompts/multimodal_analysis_prompt.md"
  }
  source {
    content  = file("${path.module}/../prompts/transcript_analysis_prompt.md")
    filename = "prompts/transcript_analysis_prompt.md"
  }
  source {
    content  = file("${path.module}/../prompts/interrogation_questions_prompt.md")
    filename = "prompts/interrogation_questions_prompt.md"
  }
  source {
    content  = file("${path.module}/../prompts/interviewer_prompt.md")
    filename = "prompts/interviewer_prompt.md"
  }
  source {
    content  = file("${path.module}/../prompts/file_validation_prompt.md")
    filename = "prompts/file_validation_prompt.md"
  }
}

# Function App (Linux)
resource "azurerm_linux_function_app" "function_app" {
  name                = local.func_app_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id     = azurerm_service_plan.asp.id

  storage_account_name       = azurerm_storage_account.sa.name
  storage_account_access_key = azurerm_storage_account.sa.primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }
    application_insights_key = azurerm_application_insights.app_insights.instrumentation_key
  }

  app_settings = merge(
    {
      "FUNCTIONS_WORKER_RUNTIME" = "python"
      "AzureWebJobsStorage"      = azurerm_storage_account.sa.primary_connection_string
      "TELEGRAM_BOT_TOKEN"       = var.telegram_bot_token
      "GOOGLE_DRIVE_FOLDER_ID"   = var.google_drive_folder_id
      "OBSIDIAN_DRIVE_FOLDER_ID" = var.obsidian_drive_folder_id
      "KANBAN_FOLDER_ID"         = var.kanban_folder_id
      "DRIVE_POLL_INTERVAL"      = tostring(var.drive_poll_interval)
      "BEYOND_REPO_NAME"         = var.beyond_repo_name
      "LOGS_WHITELIST"           = var.logs_whitelist

      # Cosmos DB Connection
      "COSMOS_DB_ENDPOINT" = azurerm_cosmosdb_account.db_account.endpoint
      "COSMOS_DB_KEY"      = azurerm_cosmosdb_account.db_account.primary_key
      "COSMOS_DB_DATABASE" = "v2v2b-db"
    },
    {
      for label, token in var.github_tokens :
      "GITHUB_TOKEN_${upper(label)}" => token
    }
  )

  # For zip deployment
  zip_deploy_file = data.archive_file.function_source.output_path
}

# Cosmos DB Account
resource "azurerm_cosmosdb_account" "db_account" {
  name                = local.cosmos_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB" # SQL API

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
  }
}

# Cosmos DB Database
resource "azurerm_cosmosdb_sql_database" "db" {
  name                = "v2v2b-db"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.db_account.name
}

# Cosmos DB Container (Example)
resource "azurerm_cosmosdb_sql_container" "interactions" {
  name                = "interactions"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.db_account.name
  database_name       = azurerm_cosmosdb_sql_database.db.name
  partition_key_path  = "/chat_id"
}


