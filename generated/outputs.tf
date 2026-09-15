output "vnet_vnet_id" {
  value = module.vnet.vnet_id
}

output "vnet_subnet_id" {
  value = module.vnet.subnet_id
}

output "aks_cluster_id" {
  value = module.aks.cluster_id
}

output "aks_fqdn" {
  value = module.aks.fqdn
}

output "aks_kube_admin_config_raw" {
  value = module.aks.kube_admin_config_raw
}

output "storage_storage_account_id" {
  value = module.storage.storage_account_id
}

output "storage_primary_blob_endpoint" {
  value = module.storage.primary_blob_endpoint
}

output "storage_primary_connection_string" {
  value = module.storage.primary_connection_string
}
