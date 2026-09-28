output "storage_account_id" {
  value = module.storage-account.storageaccount_id
}

output "keyvault_id" {
  value = module.key-vault.keyvault_id
}

output "Datafactory_Managed_Identity_Principal_ID" {
  value = module.azurerm_data_factory.Datafactory_Managed_Identity_Principal_ID
}

output "databricks_access_connector_managed_identity_principal_id" {
  value = module.azurerm_databricks_workspace.databricks_access_connector_managed_identity_principal_id
}
