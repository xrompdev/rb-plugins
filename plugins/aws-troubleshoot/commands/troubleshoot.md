---
name: troubleshoot
description: Interactively troubleshoot performance issues for a responsibid AWS service
argument-hint: "[service-name]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
---

# AWS Service Troubleshooting Command

Guide the user through diagnosing performance issues for a specific responsibid service running on ECS Fargate.

## Settings

First, check for a settings file at `.claude/aws-troubleshoot.local.md` in the current project. If it exists, read it and extract the `terraform_path`, `environment`, `aws_region`, and `aws_profile` from the YAML frontmatter.

If no settings file exists, ask the user:
- What is the path to the terraform infrastructure directory? (default: `../terraform-infra/envs/server`)
- Which environment are they troubleshooting? (staging, beta, or prod)

## Step 1: Identify the Service

If a service name was provided as an argument, use it. Otherwise, ask the user which service is having issues.

Present the service categories to help them identify the right one:

**ALB-backed (public API):** graphql, gateway, payment, temporal-ui, shortener
**Internal services:** projector, reactor, queue, orchestrator, notification, scheduler, payment-scheduler, temporal, temporal-worker, temporal-admin-tools
**Auto-scaled workers:** php-connection-worker, php-default-worker, php-follow-up-worker, php-jobs-worker, pdf-generator

## Step 2: Read Terraform Configuration

Read the relevant Terraform files to understand the service's current configuration:

1. Read `{terraform_path}/main.tf` to find the module call for the server module
2. Read the server module's `main.tf` (follow the module source path) to find the ECS service definition
3. Read the appropriate `.tfvars` file for the environment (`staging.tfvars`, `prod.tfvars`, or `beta.tfvars`)
4. Look for the service-specific variables to determine: CPU, memory, desired_count, scaling config, health check settings

Summarize the service configuration:
- Resource allocation (CPU/memory)
- Task count and scaling settings
- Dependencies (other services, databases, queues)
- Logging destination (Datadog via Fluent Bit or CloudWatch Logs)

## Step 3: Ask About Symptoms

Ask the user what symptoms they are observing. Present these common categories:

1. **Slow response times** - API calls taking longer than expected
2. **Errors / 5XX responses** - Service returning errors
3. **Service unavailable** - Cannot reach the service at all
4. **Queue backlog growing** - Messages piling up in SQS
5. **Database slowness** - Queries taking too long
6. **Tasks restarting** - ECS tasks crashing and restarting
7. **Other** - Let user describe

## Step 4: Provide Diagnostic Commands

Based on the service type and symptoms, suggest specific AWS CLI commands the user can run. Format each command as a code block they can copy-paste.

**Always include these baseline checks:**
- ECS service status (describe-services)
- Running task count vs desired count
- Recent ECS events

**Then add symptom-specific commands** from the troubleshooting playbooks in the aws-infra-knowledge skill's `references/troubleshooting-playbooks.md`.

Replace placeholders in commands with actual values:
- `{env}` -> the actual environment name (staging, prod, beta)
- `{service}` -> the actual service name
- Use the correct queue names for the environment
- Use the correct account ID (914958427285 for staging, 010946340561 for prod)

## Step 5: Provide Recommendations

After suggesting diagnostic commands, also provide:

1. **Quick wins to try** - Common fixes that often resolve the issue
2. **Terraform changes to consider** - If the issue suggests resource constraints, suggest specific Terraform variable changes (with the actual variable names from the tfvars files)
3. **Escalation path** - What to check next if the initial diagnostics don't reveal the issue
4. **Monitoring to add** - Any missing CloudWatch alarms or dashboards that would help catch this earlier

## Formatting

Present all AWS CLI commands in fenced code blocks with `bash` syntax highlighting. Include a brief explanation before each command explaining what it checks and what to look for in the output.

Group commands by diagnostic area (e.g., "ECS Health", "ALB Metrics", "Database Performance") with clear headers.

End with a summary section listing the most likely causes ranked by probability based on the symptoms described.
