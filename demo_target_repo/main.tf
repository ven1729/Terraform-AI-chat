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
