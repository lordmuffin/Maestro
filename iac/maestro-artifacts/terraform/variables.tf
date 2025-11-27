variable "gcp_project" {
  description = "The GCP project ID where resources will be created"
  type        = string
}

variable "region" {
  description = "The GCP region for resource deployment"
  type        = string
  default     = "us-central1"
}

variable "function_name" {
  description = "Name of the Cloud Function"
  type        = string
  default     = "v2v2b-interrogator"
}

variable "github_tokens" {
  description = "Map of GitHub tokens for each repository (key: repo label, value: token)"
  type        = map(string)
  sensitive   = true

  validation {
    condition     = length(var.github_tokens) > 0
    error_message = "At least one GitHub token must be provided"
  }
}

variable "repos_config_file" {
  description = "Path to repository configuration file (JSON or YAML)"
  type        = string
  default     = "repos.json"
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token obtained from @BotFather"
  type        = string
  sensitive   = true
}

variable "function_url" {
  description = "The URL of the deployed function (auto-populated after first deployment)"
  type        = string
  default     = ""
}

variable "memory" {
  description = "Memory allocation for the Cloud Function"
  type        = string
  default     = "512Mi"

  validation {
    condition     = can(regex("^[0-9]+(Mi|Gi)$", var.memory))
    error_message = "Memory must be specified in Mi or Gi (e.g., 512Mi, 1Gi)"
  }
}

variable "timeout_seconds" {
  description = "Maximum execution time for the function in seconds"
  type        = number
  default     = 540

  validation {
    condition     = var.timeout_seconds >= 1 && var.timeout_seconds <= 3600
    error_message = "Timeout must be between 1 and 3600 seconds"
  }
}

variable "max_instance_count" {
  description = "Maximum number of function instances"
  type        = number
  default     = 10

  validation {
    condition     = var.max_instance_count >= 1 && var.max_instance_count <= 1000
    error_message = "Max instance count must be between 1 and 1000"
  }
}

variable "min_instance_count" {
  description = "Minimum number of function instances (0 for scale-to-zero)"
  type        = number
  default     = 0

  validation {
    condition     = var.min_instance_count >= 0 && var.min_instance_count <= 100
    error_message = "Min instance count must be between 0 and 100"
  }
}

variable "deploy_firestore_rules" {
  description = "Whether to deploy Firestore security rules"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    application = "v2v2b-interrogator"
    managed-by  = "terraform"
    environment = "production"
  }
}

variable "google_drive_folder_id" {
  description = "Google Drive folder ID to monitor for transcripts (.txt, .m4a files)"
  type        = string
  default     = ""
}

variable "obsidian_drive_folder_id" {
  description = "Google Drive folder ID for Obsidian vault (where summaries are synced)"
  type        = string
  default     = ""
}

variable "kanban_folder_id" {
  description = "Google Drive folder ID for Kanban board folder"
  type        = string
  default     = ""
}

variable "drive_poll_interval" {
  description = "Seconds between Drive folder checks (only used if webhooks fail)"
  type        = number
  default     = 300

  validation {
    condition     = var.drive_poll_interval >= 60 && var.drive_poll_interval <= 3600
    error_message = "Poll interval must be between 60 and 3600 seconds"
  }
}
variable "custom_mcp_endpoint_url" {
  description = "The full HTTPS/HTTP endpoint URL of the externally deployed custom MCP server. (e.g., https://my-tool.example.com/v1)"
  type        = string
  default     = null
}

variable "custom_mcp_auth_secret_name" {
  description = "(Optional) The GCP Secret Manager Secret ID/Name (e.g., my-mcp-api-key) containing the API Key or Token for authentication."
  type        = string
  default     = null
}
