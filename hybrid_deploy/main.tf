terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.99"
    }
  }
}

provider "aws" {
  region = "eu-west-2"
}

module "ecs-compute" {
  source = "orchestra-hq/ecs-compute/aws"

  # REPLACE MY VALUES
  region               = "eu-west-2"
  name_prefix          = "name-prefix"
  orchestra_account_id = "YOUR_ACCOUNT_ID"
  integrations         = ["python", "dbt_core"]
}

data "aws_security_groups" "security_groups" {}
data "aws_subnets" "subnets" {}

output "ecs-compute-outputs" {
  value = module.ecs-compute
}

output "security_groups" {
  value = data.aws_security_groups.security_groups.ids
}

output "subnets" {
  value = data.aws_subnets.subnets.ids
}
