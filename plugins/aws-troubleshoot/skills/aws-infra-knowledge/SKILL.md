---
name: AWS Infrastructure Knowledge
description: >-
  This skill should be used when the user asks to "troubleshoot a service",
  "debug performance issues", "check service health", "investigate slow response times",
  "diagnose ECS task failures", "check queue backlog", "investigate database performance",
  "check ALB health", "why is the service slow", or "service is down" for the responsibid
  microservices platform. This skill should also be used when the user mentions specific
  service names like graphql, gateway, payment, temporal, orchestrator, reactor, projector,
  or PHP workers in an AWS infrastructure context.
version: 0.1.0
---

# AWS Infrastructure Knowledge

Specialized knowledge base for the responsibid AWS ECS/Fargate microservices platform.
Provides service architecture details, dependency maps, and troubleshooting guidance
for diagnosing performance issues across staging, beta, and production environments.

## Settings

Read the user's settings from `.claude/aws-troubleshoot.local.md` for the terraform path
configuration. If no settings file exists, prompt the user to specify their terraform path.

Expected settings format (YAML frontmatter):
```yaml
---
terraform_path: ../terraform-infra/envs/server
environment: staging
aws_region: us-east-1
aws_profile: default
---
```

## Architecture Overview

The platform runs 20+ ECS Fargate services in `us-east-1` across 3 availability zones.
Environments (staging, beta, prod) are managed via Terraform workspaces from a single
codebase at the configured terraform path (see Settings below).

**Networking:**
- VPC with public subnets (ALBs) and private subnets (ECS tasks)
- NAT gateway for outbound traffic from private subnets
- Cloud Map private DNS namespace: `{env}-server.local`
- Internal service URLs: `http://{service}.{env}-server.local:{port}`

**Observability stack:**
- CloudWatch alarms for unhealthy ALB hosts and ECS CPU (missing data = no tasks)
- CloudWatch dashboard: `{env}-microservices-dashboard`
- Datadog via Fluent Bit sidecar (most services) or CloudWatch Logs (workers, scheduler)
- SNS alerts: staging -> Discord, prod -> broadcast-alarms

## Service Categories

### ALB-Backed Services (public-facing)

| Service | Port | Prod Domain |
|---------|------|-------------|
| graphql | 3333 | api.bids.responsibid.com |
| gateway | 3337 | api-gateway.bids.responsibid.com |
| payment | 3336 | api-payment.bids.responsibid.com |
| temporal-ui | 8080 | temporal.bids.responsibid.com |
| shortener | 3000 | responsi.bid (prod only) |

### Internal Services (no ALB)

| Service | Port | Purpose |
|---------|------|---------|
| projector | 3334 | Event projector |
| reactor | 3335 | Event reactor |
| queue | 3336 | Queue processing |
| orchestrator | 3338 | Workflow orchestrator (Temporal) |
| notification | 3339 | Email via Mailgun |
| scheduler | 3333 | Cron scheduler (1 task) |
| payment-scheduler | 3336 | Payment cron (1 task) |
| temporal | 7233 | Temporal server |
| temporal-worker | 3339 | Custom Temporal worker |
| temporal-admin-tools | 3342 | Temporal admin CLI |

### Auto-Scaled PHP Workers

| Service | Port | Queue | Scaling |
|---------|------|-------|---------|
| php-connection-worker | 8081 | connections | SQS depth (min 5, max 150) |
| php-default-worker | 8082 | default | SQS depth (min 5, max 150) |
| php-follow-up-worker | 8083 | follow-up | SQS depth (min 5, max 150) |
| php-jobs-worker | 8084 | jobs | SQS depth (prod only) |
| pdf-generator | 3341 | N/A | CPU-based (min 1, max 3-10) |

### Databases

| Instance | Engine | Default Size | Purpose |
|----------|--------|-------------|---------|
| payment-postgres | PostgreSQL 17.4 | db.t4g.micro | Payment service |
| temporal-postgres | PostgreSQL 12/17 | db.t4g.micro | Temporal engine |

## Troubleshooting Decision Tree

When investigating a performance issue, follow this decision tree:

1. **Identify the service** - Map the user's complaint to a specific service name
2. **Classify the issue type**:
   - High latency / slow responses -> check CPU, memory, task count, ALB metrics
   - Errors / 5XX responses -> check unhealthy hosts, task health, logs
   - Queue backlog -> check SQS depth, worker scaling, message age
   - Database issues -> check RDS CPU, connections, storage, latency
   - Service unreachable -> check task count, Cloud Map registration, security groups
3. **Read Terraform config** for the specific service to understand resource limits
4. **Suggest AWS CLI commands** appropriate to the issue type

## Additional Resources

### Reference Files

Read these reference files when detailed service configurations or step-by-step diagnostic commands are needed:

- **`references/service-catalog.md`** - Complete service catalog with resource configurations,
  dependencies, environment variables, and scaling parameters for every service
- **`references/troubleshooting-playbooks.md`** - Step-by-step troubleshooting playbooks
  organized by symptom type, with specific AWS CLI commands for each diagnostic step

### Terraform Reading Guide

When reading Terraform configs for a service, look for these key parameters:
- `cpu` / `memory` - Container resource limits
- `desired_count` - Number of running tasks
- `health_check_grace_period_seconds` - Time before health checks start
- `enable_autoscaling` - Whether auto-scaling is configured
- `min_capacity` / `max_capacity` - Scaling bounds
- `common_environment` / `common_secrets` - Shared env vars and secrets
- Service-specific `environment` and `secrets` blocks
