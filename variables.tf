variable "tenant_id" { type = string }
variable "subscription_id" { type = string }
variable "dpc_code" { type = string }
variable "eai_code" { type = string }
variable "environment" { type = string }

variable "role_definition_storage_blob_data_contributor" {
  description = "Role definition key for Storage Blob Data Contributor"
  type        = string
}
