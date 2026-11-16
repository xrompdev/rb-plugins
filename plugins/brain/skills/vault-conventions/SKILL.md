---
name: vault-conventions
description: >
  Use when development work produces knowledge worth preserving: debugging sessions that reveal
  root causes, architectural decisions made during implementation, non-obvious behaviors discovered,
  or PR reviews completed. Triggers when you encounter patterns like: "the reason this breaks is...",
  "we decided to go with...", "watch out for...", "turns out the issue was...", "TIL...",
  "this is because...", "the gotcha here is...", or when completing troubleshooting, making
  design choices between alternatives, or finishing a code review. Also triggers on explicit
  requests to "save this", "write this down", "add to vault", "capture this", "log this".
version: 0.1.0
---

# ResponsiBid Obsidian Vault Conventions

The ResponsiBid second brain lives at `/home/xromp/obsidian/responsibid-brain/`. When development work produces reusable knowledge, capture it as a vault note using the conventions below.

## Vault Structure

```
responsibid-brain/
├── Projects/           # Service-specific docs, troubleshooting, gotchas
│   ├── client-v2/
│   ├── server-graphql/
│   ├── server-gateway/
│   ├── server-payment/
│   ├── server-orchestrator/
│   ├── server-projector/
│   ├── server-reactor/
│   ├── server-notification/
│   ├── server-pdf-service/
│   ├── server-temporal-worker/
│   ├── server-queue/
│   ├── legacy-php/
│   ├── subscriptions/
│   └── _infrastructure/
├── Decisions/          # Architectural decision records
├── Reviews/            # PR review notes
├── Daily/              # Daily work logs (YYYY-MM-DD.md)
├── Cross-Cutting/      # System-wide patterns and concerns
├── Routines/           # Recurring procedures (don't modify)
└── Templates/          # Note templates (don't modify)
```

## Note Types & Frontmatter

### Decision (`Decisions/{slug}.md`)
```yaml
---
type: decision
date: YYYY-MM-DD
status: accepted    # proposed | accepted | superseded
services: [server-payment, server-orchestrator]
---
```
Sections: Context, Options considered, Decision, Consequences

### Troubleshooting (`Projects/{service}/{slug}.md`)
```yaml
---
type: troubleshooting
date: YYYY-MM-DD
services: [server-payment]
resolved: true
---
```
Sections: Symptom, Cause, Fix, Prevention

### Gotcha (`Projects/{service}/{slug}.md`)
```yaml
---
type: gotcha
date: YYYY-MM-DD
services: [server-payment]
---
```
Sections: What to know, Why it matters

### PR Review (`Reviews/{PR#}-{slug}.md`)
```yaml
---
type: review
date: YYYY-MM-DD
pr: 342
repo: responsibid-server
author: username
status: approved    # approved | changes-requested | commented
---
```
Sections: Summary, Key changes, Concerns / feedback, Follow-ups

### Daily (`Daily/YYYY-MM-DD.md`)
```yaml
---
type: daily
date: YYYY-MM-DD
---
```
Sections: What I worked on, Decisions made, PRs reviewed, Blockers, Tomorrow

## Conventions

- **Filenames**: kebab-case slugs derived from the topic. Examples: `payment-webhook-timeout.md`, `342-fix-invoice-total.md`
- **Wiki-links**: Reference services and other notes with `[[service-name]]` or `[[note-name]]`
- **Services array**: Use bare names matching the Projects/ subdirectory names
- **Dates**: Always `YYYY-MM-DD` format, use today's actual date
- **Conciseness**: Notes are references, not narratives. Keep sections brief.
- **No duplicates**: Check if a similar note exists before creating a new one

## When to Capture

Offer to capture a vault note when you notice:

1. **A decision was made** between alternatives during implementation — "we went with X because Y"
2. **A bug was debugged** and the root cause was non-obvious — save the symptom → cause → fix chain
3. **A gotcha was discovered** — something surprising that would bite the next person
4. **A PR was reviewed** — save the summary and any concerns for future reference

When offering, be brief: "Want me to save this to the vault as a troubleshooting note?" If the user agrees, write the note using the templates above. Don't interrupt flow — offer at natural pause points.

## How to Capture

1. Get today's date: `date +%Y-%m-%d`
2. Determine the note type and target directory
3. Generate a kebab-case filename from the topic
4. Check the target path doesn't already exist
5. Write the note using the appropriate template
6. Tell the user what was saved and where
