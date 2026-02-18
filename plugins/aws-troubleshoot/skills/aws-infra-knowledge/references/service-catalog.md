# Service Catalog - Responsibid Platform

Complete reference for all ECS Fargate services with resource configurations, dependencies,
and operational details.

## Resource Defaults by Environment

### Staging

| Service | CPU | Memory | Tasks | Notes |
|---------|-----|--------|-------|-------|
| graphql | 512 | 1024 | 1 | Main API server |
| gateway | 256 | 512 | 1 | Apollo Federation |
| payment | 256 | 512 | 1 | Payment processing |
| payment-scheduler | 256 | 512 | 1 | Cron, single instance |
| projector | 256 | 512 | 1 | Event projection |
| reactor | 256 | 512 | 1 | Event reaction |
| queue | 256 | 512 | 1 | Queue service |
| scheduler | 256 | 512 | 1 | Cron, single instance |
| notification | 256 | 512 | 1 | Mailgun integration |
| orchestrator | 256 | 512 | 1 | Temporal workflows |
| temporal | 512 | 1024 | 1 | Temporal server |
| temporal-worker | 256 | 512 | 1 | Custom worker |
| temporal-admin-tools | 256 | 512 | 1 | Admin CLI |
| temporal-ui | 256 | 512 | 1 | Dashboard |
| php-connection-worker | 256 | 512 | 5-150 | SQS auto-scaled |
| php-default-worker | 256 | 512 | 5-150 | SQS auto-scaled |
| php-follow-up-worker | 256 | 512 | 5-150 | SQS auto-scaled |
| pdf-generator | 512 | 1024 | 1-3 | CPU auto-scaled |

### Production

| Service | CPU | Memory | Tasks | Notes |
|---------|-----|--------|-------|-------|
| graphql | 1024 | 2048 | 3 | Higher resources for prod |
| gateway | 512 | 1024 | 2 | Scaled for traffic |
| payment | 512 | 1024 | 2 | Scaled for reliability |
| php-connection-worker | 256 | 512 | 5-150 | Higher burst limits |
| php-default-worker | 256 | 512 | 5-150 | Higher burst limits |
| php-follow-up-worker | 256 | 512 | 5-150 | Higher burst limits |
| php-jobs-worker | 256 | 512 | 5-150 | Prod only |
| pdf-generator | 1024 | 2048 | 1-10 | Higher CPU for PDF rendering |
| shortener | 256 | 512 | 1 | Prod only |

## Service Dependencies

### Internal Service Communication (via Cloud Map)

```
gateway (Apollo Federation)
├── graphql (http://graphql.{env}-server.local:3333)
└── payment (http://payment.{env}-server.local:3336)

orchestrator
├── graphql (internal API calls)
├── temporal (gRPC on port 7233)
└── notification (http://notification.{env}-server.local:3339)

graphql
├── payment (http://payment.{env}-server.local:3336)
├── orchestrator (http://orchestrator.{env}-server.local:3338)
├── pdf-generator (http://pdf-generator.{env}-server.local:3341)
└── notification (http://notification.{env}-server.local:3339)

temporal-worker
└── temporal (gRPC on port 7233)
```

### External Dependencies

| Service | External Dependency | Purpose |
|---------|-------------------|---------|
| payment | Payabli API | Payment processing |
| notification | Mailgun API | Email delivery |
| graphql | Amazon MQ (RabbitMQ) | Event streaming |
| all services | RDS PostgreSQL | Data persistence |
| php-workers | SQS queues | Job processing |
| all services | Secrets Manager | Credential retrieval |
| all services | ECR | Container images |

## SQS Queue Names

### Staging
- `rbs-staging-queue-connections`
- `rbs-staging-queue-default`
- `rbs-staging-queue-follow-up`

### Production
- `rb-legacy-queue-connections`
- `rb-legacy-queue-default`
- `rb-legacy-queue-followup`
- `rb-legacy-queue-jobs`

## Auto-Scaling Configuration

### PHP Workers (SQS-based, 3-tier)

**Target Tracking (primary):**
- Target: 50 messages per task
- Scale-out cooldown: 30 seconds
- Scale-in cooldown: 180 seconds

**Step Scaling - Moderate Load:**
- Trigger: ApproximateNumberOfMessagesVisible > 1000
- Actions: 1000-2000 msgs -> 10 tasks, 2000-3000 msgs -> 20 tasks, 3000+ msgs -> 30 tasks

**Step Scaling - Burst Load:**
- Trigger: ApproximateNumberOfMessagesVisible > 5000
- Actions: 5000-10000 msgs -> 50 tasks, 10000+ msgs -> 100 tasks

**Scale-in:**
- Trigger: Messages < min_messages_per_task * min_capacity (125 by default)
- Action: Scale to min capacity (5)

### PDF Generator (CPU-based)

- Target: 70% CPU utilization
- Scale-out cooldown: 60 seconds
- Scale-in cooldown: 120 seconds
- Min: 1 task, Max: 3 (staging) / 10 (prod)

## CloudWatch Alarms

### ALB Health Alarms
- `{env}-gateway-unhealthy-hosts` - UnHealthyHostCount >= 1
- `{env}-graphql-unhealthy-hosts` - UnHealthyHostCount >= 1
- `{env}-payment-unhealthy-hosts` - UnHealthyHostCount >= 1
- `{env}-temporal-ui-unhealthy-hosts` - UnHealthyHostCount >= 1

### ECS Service Health Alarms
- `{env}-{service}-service-health` - CPUUtilization missing data (no running tasks)
- Applies to all services
- Treat missing data as breaching (2 consecutive 60s periods)

### SQS Alarms (auto-scaled workers)
- `{env}-{service}-queue-depth-moderate` - Messages > 1000
- `{env}-{service}-queue-depth-high` - Messages > 5000
- `{env}-{service}-queue-depth-low` - Messages < 125
- `{env}-{service}-message-age-critical` - Oldest message > 60 seconds

## Logging Destinations

| Service | Log Destination | Log Group |
|---------|----------------|-----------|
| graphql | Datadog (Fluent Bit) | N/A (via firelens) |
| gateway | Datadog (Fluent Bit) | N/A (via firelens) |
| payment | Datadog (Fluent Bit) | N/A (via firelens) |
| orchestrator | Datadog (Fluent Bit) | N/A (via firelens) |
| notification | Datadog (Fluent Bit) | N/A (via firelens) |
| temporal-ui | CloudWatch Logs | /ecs/{env}-server/temporal-ui |
| shortener | CloudWatch Logs | /ecs/{env}-server/shortener |
| scheduler | CloudWatch Logs | /ecs/{env}-server/scheduler |
| payment-scheduler | CloudWatch Logs | /ecs/{env}-server/payment-scheduler |
| php-*-worker | CloudWatch Logs | /ecs/{env}-server/php-{type}-worker |
| pdf-generator | CloudWatch Logs | /ecs/{env}-server/pdf-generator |

## ECR Image Registry

All images stored in ECR: `914958427285.dkr.ecr.us-east-1.amazonaws.com`

Image repositories follow service names:
- `graphql-server`
- `payment`
- `gateway`
- `orchestrator`
- `notification`
- `pdf-generator`
- `shortener`
- `queue`
- etc.
