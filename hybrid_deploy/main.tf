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
  source  = "orchestra-hq/ecs-compute/aws"
  version = "0.0.2"

  # REPLACE MY VALUES
  region               = "eu-west-2"
  name_prefix          = "test-deploy"
  orchestra_account_id = "266858c8-2872-4b09-bdfb-74d91cc990ba"
  integrations         = ["python"]
}

data "aws_security_groups" "security_groups" {}
data "aws_subnets" "subnets" {}

output "ecs-compute-outputs" {
  value = module.ecs-compute
}

output "security_groups" {
  value = data.aws_security_groups.security_groups
}

output "subnets" {
  value = data.aws_subnets.subnets
}
