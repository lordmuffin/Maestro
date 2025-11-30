output "function_app_name" {
  value = azurerm_linux_function_app.function.name
}

output "function_app_default_hostname" {
  value = azurerm_linux_function_app.function.default_hostname
}
