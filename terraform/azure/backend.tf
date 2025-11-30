terraform {
  backend "azurerm" {
    # The following values are expected to be provided via
    # -backend-config command line arguments or a backend.conf file
    # during 'tofu init'.
    #
    # resource_group_name  = "rg-maestro-terraform-state"
    # storage_account_name = "stmaestrotf..."
    # container_name       = "tfstate"
    # key                  = "prod.terraform.tfstate"
  }
}
