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
