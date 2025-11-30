variable "location" {
  description = "The Azure region to deploy resources to."
  type        = string
  default     = "eastus"
}

variable "project_name" {
  description = "The name of the project, used for naming resources."
  type        = string
  default     = "maestro-v2v2b"
}

variable "environment" {
  description = "The deployment environment (e.g., dev, prod)."
  type        = string
  default     = "prod"
}

variable "telegram_bot_token" {
  description = "The Telegram Bot Token."
  type        = string
  sensitive   = true
}

variable "gcp_project_id" {
  description = "GCP Project ID for legacy integrations (optional)"
  type        = string
  default     = ""
}
