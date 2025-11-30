mock_provider "google" {}
mock_provider "archive" {}

variables {
  gcp_project = "test-project"
  region      = "us-central1"
  function_name = "v2v2b-interrogator"
  github_tokens = {
    maestro = "test-token"
    beyond = "test-token"
  }
  telegram_bot_token = "test-bot-token"
  google_drive_folder_id = "test-id"
}

run "unit_validation" {
  command = plan

  assert {
    condition     = var.gcp_project != ""
    error_message = "Project ID must be set"
  }
}
