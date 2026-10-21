terraform {
  required_version = ">= 1.5.0"
}

module "key-vault" {
  source  = "app.terraform.io/MetLife-Global/key-vault/azurerm"
  version = "2.1.1"
}

module "storage-account" {
  source  = "app.terraform.io/MetLife-Global/storage-account/azurerm"
  version = "2.0.6"
}

module "azurerm_data_factory" {
  source  = "app.terraform.io/MetLife-Global/data-factory/azurerm"
  version = "2.0.4"
}

module "azurerm_databricks_workspace" {
  source  = "app.terraform.io/MetLife-Global/azure-databricks/azurerm"
  version = "2.2.2"
}

# Added by Terraform Access Studio; review the plan before apply.
module "iam_group_role_assignment_req-demo-001_access_1_1_storage_blob_data_contributor" {
  source  = "app.terraform.io/MetLife-Global/iam-group-role-assignment/azurerm"
  version = "1.0.6"

  role_definition = var.role_definition_storage_blob_data_contributor
  scope           = module.storage-account.storageaccount_id
  group_object_id   = var.group_object_id_access_1_1
  approver_group_id = var.approver_group_id_access_1_1
}

# Added by Terraform Access Studio; review the plan before apply.
module "iam_role_assignment_req-demo-001_access_2_2_key_vault_secrets_officer" {
  source  = "app.terraform.io/MetLife-Global/iam-role-assignment/azurerm"
  version = "3.0.1"

  role_definition = var.role_definition_keyvault_secret_officer
  scope           = module.key-vault.keyvault_id
  principal_id    = module.azurerm_data_factory.Datafactory_Managed_Identity_Principal_ID
  principal_type  = "ServicePrincipal"
}
