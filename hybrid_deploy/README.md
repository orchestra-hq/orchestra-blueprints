# Deploying Hybrid Compute Terraform

1. Ensure the AWS IAM role deploying the Terraform has the correct permissions to create the resources.
2. Provide the required variables to the Terraform module.
3. Run `terraform init` to initialize the Terraform state.
4. Run `terraform plan` to see the changes that will be applied.
5. Run `terraform apply` to apply the changes.

To remove the resources, run `terraform destroy`.
