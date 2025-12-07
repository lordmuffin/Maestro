# Staging Environment Configuration
# This file contains staging-specific variable values for Terraform

# Cloud Function Configuration
function_name      = "v2v2b-interrogator"
memory             = "512Mi"
max_instance_count = 5
min_instance_count = 0
timeout_seconds    = 540

# Resource Labels
labels = {
  environment = "staging"
  managed-by  = "terraform"
  cost-center = "development"
}

# Deployment Configuration (optional overrides)
# deploy_firestore_rules = false  # Set to true to deploy Firestore rules in staging
