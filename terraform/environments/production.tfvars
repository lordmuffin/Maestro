# Production Environment Configuration
# This file contains production-specific variable values for Terraform

# Cloud Function Configuration
function_name      = "v2v2b-interrogator"
memory             = "1Gi"
cpu                = "1"
max_instance_count = 10
min_instance_count = 1
timeout_seconds    = 540

# Resource Labels
labels = {
  environment = "production"
  managed-by  = "terraform"
  cost-center = "production"
}

# Deployment Configuration
deploy_firestore_rules = true # Deploy security rules in production
