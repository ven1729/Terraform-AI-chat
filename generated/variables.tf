variable "account_name" {
  type        = string
  description = "Globally unique storage account name."
}

variable "account_replication_type" {
  type        = string
  description = "Replication type."
  default     = "LRS"
}

variable "account_tier" {
  type        = string
  description = "Storage tier."
  default     = "Standard"
}

variable "address_space" {
  type        = list(string)
  description = "VNet address space."
  default     = ["10.0.0.0/16"]
}

variable "cluster_name" {
  type        = string
  description = "Name of the AKS cluster."
}

variable "dns_prefix" {
  type        = string
  description = "DNS prefix."
}

variable "enable_https_traffic_only" {
  type        = bool
  description = "HTTPS only."
  default     = true
}

variable "kind" {
  type        = string
  description = "Storage kind."
  default     = "StorageV2"
}

variable "kubernetes_version" {
  type        = string
  description = "Kubernetes version."
  default     = "1.31"
}

variable "location" {
  type        = string
  description = "Azure location."
  default     = "eastus"
}

variable "node_count" {
  type        = number
  description = "Node count."
  default     = 2
}

variable "node_pool_name" {
  type        = string
  description = "Node pool name."
  default     = "system"
}

variable "node_vm_size" {
  type        = string
  description = "Node VM size."
  default     = "Standard_D4s_v5"
}

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group where the VNet will be created."
}

variable "subnet_id" {
  type        = string
  description = "AKS subnet ID."
}

variable "subnet_name" {
  type        = string
  description = "Subnet name."
  default     = "subnet1"
}

variable "subnet_prefixes" {
  type        = list(string)
  description = "Subnet CIDR prefixes."
  default     = ["10.0.1.0/24"]
}

variable "tags" {
  type        = map(string)
  description = "Tags."
  default     = {  }
}

variable "vnet_name" {
  type        = string
  description = "Name of the virtual network."
  default     = "example-vnet"
}
