# Demo target repository

module "key-vault" {
  source = "./modules/key-vault"
}

module "storage-account" {
  source = "./modules/storage-account"
}

module "azurerm_data_factory" {
  source = "./modules/data-factory"
}

module "azurerm_databricks_workspace" {
  source = "./modules/databricks"
}

module "iam-group-role-assignment_key_vault_req_demo_001" {
  source  = "app.terraform.io/MetLife-Global/iam-group-role-assignment/azurerm"
  version = "1.0.6"

  tenant_id       = var.tenant_id
  subscription_id = var.subscription_id
  dpc_code        = var.dpc_code
  eai_code        = var.eai_code
  environment     = var.environment

  role_definition_name = var.role_definition_keyvault_secret_officer
  scope                = module.key-vault.keyvault_id[0]
  group_object_id      = var.group_object_id
  approver_group_id    = var.approver_group_id

  custom_tags = {
    SCM_COMMIT_ID = var.TFC_CONFIGURATION_VERSION_GIT_COMMIT_SHA
  }
}
