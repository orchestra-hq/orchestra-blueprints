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
  # source = "../../terraform-aws-ecs-compute"
  source  = "orchestra-hq/ecs-compute/aws"
  version = "1.0.0"

  # REPLACE MY VALUES
  region                   = "eu-west-2"
  name_prefix              = "test-v6"
  orchestra_account_id     = "84e75049-b4c3-4a93-a595-21cff92bdb9d"
  orchestra_aws_account_id = "383742555833"
  integrations             = ["python"]
  image_tags = {
    "python" : "54896a6c885f73ae629e4390cc2361127f409f9d"
  }
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
