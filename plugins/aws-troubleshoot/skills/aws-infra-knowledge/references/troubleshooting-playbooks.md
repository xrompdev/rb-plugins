# Troubleshooting Playbooks

Step-by-step diagnostic procedures organized by symptom type. Each playbook includes
specific AWS CLI commands to suggest to the user.

## Playbook 1: High Latency / Slow Response Times

**Applies to:** ALB-backed services (graphql, gateway, payment, temporal-ui, shortener)

### Step 1: Check ALB Target Response Time

```bash
# Get P95 response time for the last 30 minutes
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value={alb-arn-suffix} \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics p95 p99 Average \
  --region us-east-1
```

**What to look for:** P95 above 1s for API services indicates a problem.

### Step 2: Check ECS Task CPU and Memory

```bash
# Get CPU utilization for the service
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value={env}-server Name=ServiceName,Value={env}-server-{service} \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1

# Get Memory utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ClusterName,Value={env}-server Name=ServiceName,Value={env}-server-{service} \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1
```

**Thresholds:**
- CPU > 80% sustained: Consider increasing CPU allocation or task count
- Memory > 85%: Risk of OOM kills, increase memory allocation
- CPU > 95%: Immediate scaling needed

### Step 3: Check Running Task Count

```bash
aws ecs describe-services \
  --cluster {env}-server \
  --services {env}-server-{service} \
  --region us-east-1 \
  --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}'
```

**What to look for:** running < desired indicates tasks are failing to start or being killed.

### Step 4: Check for 5XX Errors

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value={alb-arn-suffix} \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

### Step 5: Check Recent Deployments

```bash
aws ecs describe-services \
  --cluster {env}-server \
  --services {env}-server-{service} \
  --region us-east-1 \
  --query 'services[0].deployments[*].{status:status,running:runningCount,desired:desiredCount,created:createdAt}'
```

**What to look for:** Multiple deployments indicate rolling update in progress or failed deployment.

### Recommendations Based on Findings

- **High CPU + normal memory**: Increase CPU units or add more tasks
- **High memory + normal CPU**: Increase memory allocation, check for memory leaks
- **Both high**: Increase both resources and task count
- **Normal metrics but slow**: Check downstream dependencies (database, external APIs)
- **Tasks restarting**: Check logs for OOM kills or application errors

---

## Playbook 2: Service Unavailable / Unhealthy Hosts

**Applies to:** All services, especially ALB-backed

### Step 1: Check ALB Target Health

```bash
# Get target group ARN first
aws elbv2 describe-target-groups \
  --names {env}-server-{service}-tg \
  --region us-east-1 \
  --query 'TargetGroups[0].TargetGroupArn' --output text

# Then check target health
aws elbv2 describe-target-health \
  --target-group-arn {target-group-arn} \
  --region us-east-1
```

**What to look for:** Targets in `unhealthy` or `draining` state.

### Step 2: Check ECS Task Status

```bash
# List tasks for the service
aws ecs list-tasks \
  --cluster {env}-server \
  --service-name {env}-server-{service} \
  --region us-east-1

# Describe tasks to see status and stop reasons
aws ecs describe-tasks \
  --cluster {env}-server \
  --tasks {task-arns} \
  --region us-east-1 \
  --query 'tasks[*].{id:taskArn,status:lastStatus,stopCode:stopCode,stopReason:stoppedReason,health:healthStatus}'
```

### Step 3: Check Stopped Tasks

```bash
aws ecs list-tasks \
  --cluster {env}-server \
  --service-name {env}-server-{service} \
  --desired-status STOPPED \
  --region us-east-1

# Describe stopped tasks for stop reasons
aws ecs describe-tasks \
  --cluster {env}-server \
  --tasks {stopped-task-arns} \
  --region us-east-1 \
  --query 'tasks[*].{stopCode:stopCode,stopReason:stoppedReason,exitCode:containers[0].exitCode}'
```

### Step 4: Check CloudWatch Logs

```bash
# For services using CloudWatch Logs
aws logs get-log-events \
  --log-group-name /ecs/{env}-server/{service} \
  --log-stream-name $(aws logs describe-log-streams \
    --log-group-name /ecs/{env}-server/{service} \
    --order-by LastEventTime --descending --limit 1 \
    --query 'logStreams[0].logStreamName' --output text) \
  --limit 50 \
  --region us-east-1
```

### Step 5: Check ECS Events

```bash
aws ecs describe-services \
  --cluster {env}-server \
  --services {env}-server-{service} \
  --region us-east-1 \
  --query 'services[0].events[:10]'
```

**What to look for:** Repeated "has reached a steady state" quickly followed by task stops
indicates a crash loop.

### Common Causes

- **Exit code 137**: OOM kill - increase memory allocation
- **Exit code 1**: Application error - check logs
- **Health check failing**: Application not responding on health check path within grace period
- **Image pull failure**: ECR authentication or image not found
- **Secrets Manager failure**: Missing or inaccessible secrets

---

## Playbook 3: SQS Queue Backlog

**Applies to:** PHP workers (connection, default, follow-up, jobs), queue service

### Step 1: Check Queue Depth

```bash
# Get queue attributes
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/{account-id}/{queue-name} \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible ApproximateNumberOfMessagesDelayed \
  --region us-east-1
```

**Queue name mapping:**
- Staging: `rbs-staging-queue-{connections|default|follow-up}`
- Prod: `rb-legacy-queue-{connections|default|followup|jobs}`

### Step 2: Check Message Age

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateAgeOfOldestMessage \
  --dimensions Name=QueueName,Value={queue-name} \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Maximum \
  --region us-east-1
```

**Thresholds:**
- Age > 60s: Critical alarm fires
- Age > 300s: Significant processing delay

### Step 3: Check Worker Task Count

```bash
aws ecs describe-services \
  --cluster {env}-server \
  --services {env}-server-php-{type}-worker \
  --region us-east-1 \
  --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}'
```

### Step 4: Check Auto-Scaling Activity

```bash
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id service/{env}-server/{env}-server-php-{type}-worker \
  --region us-east-1 \
  --max-results 10
```

### Step 5: Check Dead Letter Queue (if configured)

```bash
# Check if DLQ has messages (indicating processing failures)
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/{account-id}/{queue-name}-dlq \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1
```

### Recommendations

- **Queue growing + workers at max**: Workers can't keep up - investigate per-message processing time
- **Queue growing + workers below max**: Auto-scaling may be lagging - check scaling activities
- **Queue growing + workers failing**: Workers are crashing - check logs for errors
- **DLQ has messages**: Some messages are failing repeatedly - investigate message content
- **Message age high but queue small**: Individual messages taking too long to process

---

## Playbook 4: Database Performance Issues

**Applies to:** payment-postgres, temporal-postgres

### Step 1: Check RDS CPU Utilization

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value={env}-server-{payment|temporal}-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1
```

### Step 2: Check Database Connections

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value={env}-server-{payment|temporal}-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1
```

**db.t4g.micro connection limit:** ~85 connections max

### Step 3: Check Read/Write Latency

```bash
# Read latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReadLatency \
  --dimensions Name=DBInstanceIdentifier,Value={env}-server-{payment|temporal}-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1

# Write latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name WriteLatency \
  --dimensions Name=DBInstanceIdentifier,Value={env}-server-{payment|temporal}-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average Maximum \
  --region us-east-1
```

### Step 4: Check Free Storage Space

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value={env}-server-{payment|temporal}-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Minimum \
  --region us-east-1
```

**Storage autoscaling:** 20 GB initial, up to 100 GB max

### Step 5: Check Freeable Memory

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value={env}-server-{payment|temporal}-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Minimum Average \
  --region us-east-1
```

### Recommendations

- **High CPU**: Slow queries or too many connections - review query performance
- **Max connections reached**: Connection pool exhaustion - reduce pool size per service or upgrade instance
- **High read latency**: Missing indexes or full table scans
- **High write latency**: Storage IOPS limit hit - consider provisioned IOPS
- **Low free storage**: Storage autoscaling should handle, but monitor if near 100 GB limit
- **Low freeable memory**: Instance too small - upgrade from db.t4g.micro

---

## Playbook 5: Network / Connectivity Issues

**Applies to:** All services communicating via Cloud Map

### Step 1: Verify Cloud Map Registration

```bash
# List service instances in the namespace
aws servicediscovery list-instances \
  --service-id {cloud-map-service-id} \
  --region us-east-1
```

### Step 2: Check Security Group Rules

```bash
# Get security group for the ECS service
aws ecs describe-services \
  --cluster {env}-server \
  --services {env}-server-{service} \
  --region us-east-1 \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups'

# Check inbound rules
aws ec2 describe-security-groups \
  --group-ids {sg-id} \
  --region us-east-1 \
  --query 'SecurityGroups[0].IpPermissions'
```

### Step 3: Check NAT Gateway Health

```bash
# If services can't reach external APIs
aws ec2 describe-nat-gateways \
  --filter Name=vpc-id,Values={vpc-id} \
  --region us-east-1 \
  --query 'NatGateways[*].{id:NatGatewayId,state:State,subnet:SubnetId}'
```

### Step 4: Check VPC Endpoints (staging)

```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values={vpc-id} \
  --region us-east-1 \
  --query 'VpcEndpoints[*].{service:ServiceName,state:State}'
```

**Staging VPC endpoints:** ECR API, ECR DKR, S3, CloudWatch Logs, Secrets Manager, SSM, SQS, ECS, CloudWatch Monitoring

---

## Quick Reference: AWS CLI Account IDs

| Environment | Account ID |
|-------------|-----------|
| Staging | 914958427285 |
| Production | 010946340561 |

## Quick Reference: Common Metric Namespaces

| Resource | Namespace |
|----------|-----------|
| ECS | AWS/ECS |
| ALB | AWS/ApplicationELB |
| RDS | AWS/RDS |
| SQS | AWS/SQS |
| NAT Gateway | AWS/NATGateway |
