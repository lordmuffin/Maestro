terraform {
  backend "azurerm" {
    # These values should be passed via backend-config in the CI/CD pipeline
    # or a local backend configuration file.
    # resource_group_name  = "..."
    # storage_account_name = "..."
    # container_name       = "..."
    # key                  = "terraform.tfstate"
  }
}
