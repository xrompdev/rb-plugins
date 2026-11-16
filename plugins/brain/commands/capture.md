---
name: capture
description: Capture a decision, troubleshooting session, or gotcha into the Obsidian vault
argument-hint: "<decision|troubleshooting|gotcha> [short description]"
allowed-tools:
  - Write
  - Read
  - Edit
  - Bash
  - AskUserQuestion
---

# Capture Dev Context

Write a structured note to the ResponsiBid Obsidian vault at `/home/xromp/obsidian/responsibid-brain/`.

## Instructions

1. **Parse arguments** to determine:
   - **Type**: `decision`, `troubleshooting`, or `gotcha`
   - **Description**: Optional short description of the topic

2. If no type is provided, ask the user which type using AskUserQuestion with options: Decision, Troubleshooting, Gotcha.

3. If no description is provided, ask the user to briefly describe what happened.

4. **Gather details** based on type. Ask follow-up questions as needed, but also infer from conversation context when possible. Don't over-ask — if the conversation already contains the answers, use them.

5. **Determine the filename**: Use a kebab-case slug derived from the description. Example: "payment webhook timeout" becomes `payment-webhook-timeout.md`.

6. **Determine services**: Identify which ResponsiBid services are involved. Valid service names for wiki-links: `client-v2`, `server-graphql`, `server-gateway`, `server-payment`, `server-orchestrator`, `server-projector`, `server-reactor`, `server-notification`, `server-pdf-service`, `server-temporal-worker`, `server-queue`, `legacy-php`, `subscriptions`, `_infrastructure`.

7. **Write the note** to the correct directory using the templates below.

8. **Show the user** the file path and a brief summary of what was captured.

## Templates

### Decision → `Decisions/{slug}.md`

```markdown
---
type: decision
date: {YYYY-MM-DD}
status: accepted
services: [{service-names}]
---

## Context

{Why this decision came up — what problem or question triggered it}

## Options considered
1. {Option A — brief description}
2. {Option B — brief description}

## Decision

{What was decided and why}

## Consequences

{What this means going forward — trade-offs, follow-up work, risks}
```

### Troubleshooting → `Projects/{primary-service}/{slug}.md`

Place troubleshooting notes in the service directory of the primary affected service.

```markdown
---
type: troubleshooting
date: {YYYY-MM-DD}
services: [{service-names}]
resolved: {true|false}
---

## Symptom

{What was observed — error messages, unexpected behavior}

## Cause

{Root cause identified}

## Fix

{What was done to resolve it — include code references if relevant}

## Prevention

{How to avoid this in the future}
```

### Gotcha → `Projects/{primary-service}/{slug}.md`

Place gotcha notes in the service directory of the primary affected service.

```markdown
---
type: gotcha
date: {YYYY-MM-DD}
services: [{service-names}]
---

## What to know

{The non-obvious behavior, constraint, or trap}

## Why it matters

{What goes wrong if you don't know this}
```

## Rules

- Use today's date (check with `date +%Y-%m-%d`)
- Use wiki-links (`[[service-name]]`) when referencing services in the body text
- If a file with the same name already exists, append a numeric suffix (`-2`, `-3`)
- Keep notes concise — this is a reference, not a novel
- Infer from conversation context rather than asking questions the user already answered
- For services array in frontmatter, use bare names without brackets: `services: [server-payment, server-orchestrator]`
