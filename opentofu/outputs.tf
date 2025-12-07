output "function_name" {
  description = "Name of the deployed Function App"
  value       = azurerm_linux_function_app.function_app.name
}

output "function_url" {
  description = "The URL to invoke the Function App"
  value       = "https://${azurerm_linux_function_app.function_app.default_hostname}"
}

output "cosmos_db_endpoint" {
  description = "The endpoint of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.db_account.endpoint
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.rg.name
}

output "deployment_instructions" {
  description = "Instructions after deployment"
  value       = <<-EOT
  
  ================================================================
  Azure Function Deployment Complete
  ================================================================
  
  Function URL: https://${azurerm_linux_function_app.function_app.default_hostname}
  
  Next Steps:
  1. Set up Telegram Webhook:
     curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://${azurerm_linux_function_app.function_app.default_hostname}/api/telegram_webhook"
  
  2. Verify:
     Check the Azure Portal and Application Insights for logs.
  
  EOT
}
