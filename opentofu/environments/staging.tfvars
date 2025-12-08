# Staging Environment Configuration
# This file contains staging-specific variable values for Terraform

# Cloud Function Configuration
function_name      = "v2v2b-interrogator"


# Resource Labels
labels = {
  environment = "staging"
  managed-by  = "terraform"
  cost-center = "development"
}

# Deployment Configuration (optional overrides)
# deploy_firestore_rules = false  # Set to true to deploy Firestore rules in staging
