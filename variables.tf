variable "tenant_id" { type = string }
variable "subscription_id" { type = string }
variable "dpc_code" { type = string }
variable "eai_code" { type = string }
variable "environment" { type = string }

variable "role_definition_keyvault_contributor" {
  description = "Role definition key for Key Vault Contributor"
  type        = string
}

variable "group_object_id" {
  description = "Microsoft Entra ID group object ID"
  type        = string
}

variable "approver_group_id" {
  description = "Approver group object ID"
  type        = string
}
