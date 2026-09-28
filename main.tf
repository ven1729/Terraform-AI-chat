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
module "iam-group-role-assignment_req-demo-001" {
  source  = "app.terraform.io/MetLife-Global/iam-group-role-assignment/azurerm"
  version = "1.0.6"

  role_definition = var.role_definition_keyvault_contributor
  scope           = module.key-vault.keyvault_id
  group_object_id   = var.group_object_id
  approver_group_id = var.approver_group_id
}
