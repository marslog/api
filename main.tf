resource "null_resource" "create_vm" {
  provisioner "local-exec" {
    command = "python3 create_vm_aws4.py"
    environment = {
      access_key = var.access_key
      secret_key = var.secret_key
      scp_ip     = var.scp_ip
    }
  }
}