module "vnet" {
  source = "git::https://github.com/ven1729/umbrella.git//modules/vnet?ref=feature"
  vnet_name = var.vnet_name
  resource_group_name = var.resource_group_name
  location = var.location
  address_space = var.address_space
  subnet_name = var.subnet_name
  subnet_prefixes = var.subnet_prefixes
  tags = var.tags
}

module "aks" {
  source = "git::https://github.com/ven1729/umbrella.git//modules/aks?ref=feature"
  cluster_name = var.cluster_name
  resource_group_name = var.resource_group_name
  location = var.location
  dns_prefix = var.dns_prefix
  kubernetes_version = var.kubernetes_version
  node_pool_name = var.node_pool_name
  node_vm_size = var.node_vm_size
  node_count = var.node_count
  subnet_id = module.vnet.subnet_id
  tags = var.tags
}

module "storage" {
  source = "git::https://github.com/ven1729/umbrella.git//modules/storage?ref=feature"
  account_name = var.account_name
  resource_group_name = var.resource_group_name
  location = var.location
  account_tier = var.account_tier
  account_replication_type = var.account_replication_type
  kind = var.kind
  enable_https_traffic_only = var.enable_https_traffic_only
  tags = var.tags
}
