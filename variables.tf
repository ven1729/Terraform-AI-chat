variable "tenant_id" { type = string }
variable "subscription_id" { type = string }
variable "dpc_code" { type = string }
variable "eai_code" { type = string }
variable "environment" { type = string }

variable "role_definition_storage_blob_data_contributor" {
  description = "Approved role key for Storage Blob Data Contributor"
  type        = string
}

variable "group_object_id_task2_2" {
  description = "Microsoft Entra ID group object ID"
  type        = string
}

variable "approver_group_id_task2_2" {
  description = "Approver group object ID"
  type        = string
}
