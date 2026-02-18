# aws-troubleshoot

AWS infrastructure troubleshooting plugin for the responsibid ECS/Fargate microservices platform. Reads Terraform configurations and suggests AWS CLI commands to diagnose performance issues.

## Features

- **Interactive troubleshooting command** (`/aws-troubleshoot:troubleshoot`) - Guided step-by-step performance diagnosis
- **Infrastructure advisor agent** - Proactively activates when discussing performance issues
- **Service-specific knowledge** - Deep understanding of all 20+ responsibid services, their dependencies, scaling configs, and monitoring

## Prerequisites

- AWS CLI configured with appropriate credentials (`aws configure`)
- Access to the Terraform infrastructure repository
- CloudWatch read permissions for the target AWS account

## Installation

Add to your project's `.claude/settings.json`:

```json
{
  "plugins": [
    "/path/to/rb-plugins/aws-troubleshoot"
  ]
}
```

Or test locally:

```bash
claude --plugin-dir /path/to/rb-plugins/aws-troubleshoot
```

## Configuration

Create `.claude/aws-troubleshoot.local.md` in your project root:

```markdown
---
terraform_path: ../terraform-infra/envs/server
environment: staging
aws_region: us-east-1
aws_profile: default
---

Additional context about the infrastructure setup.
```

### Settings

| Field | Description | Default |
|-------|-------------|---------|
| `terraform_path` | Path to Terraform envs/server directory | `../terraform-infra/envs/server` |
| `environment` | Target environment (staging, beta, prod) | `staging` |
| `aws_region` | AWS region | `us-east-1` |
| `aws_profile` | AWS CLI profile name | `default` |

## Usage

### Troubleshoot Command

```
/aws-troubleshoot:troubleshoot graphql
/aws-troubleshoot:troubleshoot php-default-worker
/aws-troubleshoot:troubleshoot
```

The command will:
1. Identify the service (or ask you to pick one)
2. Read Terraform config to understand resource allocation
3. Ask about symptoms
4. Suggest specific AWS CLI diagnostic commands
5. Recommend fixes and monitoring improvements

### Infrastructure Advisor Agent

The agent activates automatically when you discuss performance issues:

- "The graphql service is running really slow in production"
- "We're seeing a lot of 5XX errors on the payment endpoint"
- "SQS queues are backing up"

## Supported Services

**ALB-backed:** graphql, gateway, payment, temporal-ui, shortener
**Internal:** projector, reactor, queue, orchestrator, notification, scheduler, payment-scheduler, temporal, temporal-worker, temporal-admin-tools
**Auto-scaled workers:** php-connection-worker, php-default-worker, php-follow-up-worker, php-jobs-worker, pdf-generator
**Databases:** payment-postgres, temporal-postgres
