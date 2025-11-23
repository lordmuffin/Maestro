output "function_name" {
  description = "Name of the deployed Cloud Function"
  value       = google_cloudfunctions2_function.v2v2b_interrogator.name
}

output "function_url" {
  description = "The URL to invoke the Cloud Function"
  value       = google_cloudfunctions2_function.v2v2b_interrogator.service_config[0].uri
}

output "function_region" {
  description = "Region where the function is deployed"
  value       = google_cloudfunctions2_function.v2v2b_interrogator.location
}

output "service_account_email" {
  description = "Email of the service account used by the function"
  value       = google_service_account.function_sa.email
}

output "firestore_database" {
  description = "Firestore database name"
  value       = google_firestore_database.database.name
}

output "function_bucket" {
  description = "GCS bucket used for function source code"
  value       = google_storage_bucket.function_bucket.name
}

output "google_chat_webhook_url" {
  description = "URL to use as Google Chat webhook endpoint"
  value       = google_cloudfunctions2_function.v2v2b_interrogator.service_config[0].uri
}

output "upload_ui_url_template" {
  description = "Template URL for file upload interface (replace SESSION_ID)"
  value       = "${google_cloudfunctions2_function.v2v2b_interrogator.service_config[0].uri}?mode=ui&session=SESSION_ID"
}

output "deployment_summary" {
  description = "Summary of deployment information"
  value = <<-EOT

  ================================================================
  V2V2B Interrogator Deployment Summary
  ================================================================

  Function Name:    ${google_cloudfunctions2_function.v2v2b_interrogator.name}
  Function URL:     ${google_cloudfunctions2_function.v2v2b_interrogator.service_config[0].uri}
  Region:           ${google_cloudfunctions2_function.v2v2b_interrogator.location}
  Service Account:  ${google_service_account.function_sa.email}

  ================================================================
  Next Steps:
  ================================================================

  1. Configure Google Chat App:
     - Go to: https://console.cloud.google.com/apis/api/chat.googleapis.com
     - Click "Configuration" → "Create Chat App"
     - Set HTTP endpoint to: ${google_cloudfunctions2_function.v2v2b_interrogator.service_config[0].uri}
     - Enable "Receive 1:1 messages" and "Join spaces"
     - Save and Publish

  2. Configure Google Drive Access (Optional):
     - Share your Drive folders with: ${google_service_account.function_sa.email}
     - Transcript folder: Grant "Viewer" access
     - Obsidian folder: Grant "Editor" access
     - Update terraform.tfvars with folder IDs and re-apply

  3. Update terraform.tfvars with the function URL:
     function_url = "${google_cloudfunctions2_function.v2v2b_interrogator.service_config[0].uri}"

  4. Test the bot:
     - Open Google Chat
     - Search for "${var.function_name}"
     - Send a message!

  5. Test Drive scan (if configured):
     curl "${google_cloudfunctions2_function.v2v2b_interrogator.service_config[0].uri}?mode=scan"

  6. View logs:
     gcloud functions logs read ${google_cloudfunctions2_function.v2v2b_interrogator.name} \
       --region=${google_cloudfunctions2_function.v2v2b_interrogator.location} \
       --gen2 --limit=50

  ================================================================

  EOT
}

output "terraform_refresh_command" {
  description = "Command to refresh Terraform state after first deployment"
  value       = "terraform refresh -var='function_url=${google_cloudfunctions2_function.v2v2b_interrogator.service_config[0].uri}'"
}
