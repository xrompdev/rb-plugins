---
name: daily
description: Create or update today's daily note with a summary of work done
allowed-tools:
  - Write
  - Read
  - Edit
  - Bash
---

# Daily Note

Create or update today's daily note in the ResponsiBid Obsidian vault.

## Instructions

1. **Get today's date**: `date +%Y-%m-%d`

2. **Check if today's note exists**: Read `/home/xromp/obsidian/responsibid-brain/Daily/{YYYY-MM-DD}.md`

3. **Gather context** from the current session. Use what you know from this conversation:
   - What was worked on (features, bugs, refactors, investigations)
   - Decisions made (link to any decision notes in `Decisions/` if they exist)
   - PRs reviewed (link to any review notes in `Reviews/` if they exist)
   - Blockers encountered
   - What's planned next

4. **If the note doesn't exist**, create it:

```markdown
---
type: daily
date: {YYYY-MM-DD}
---

## What I worked on

- {bullet points of work done}

## Decisions made

- {any decisions, or leave empty}

## PRs reviewed

- {any reviews, or leave empty}

## Blockers

- {any blockers, or leave empty}

## Tomorrow

- {next steps, or leave empty}
```

Write to: `/home/xromp/obsidian/responsibid-brain/Daily/{YYYY-MM-DD}.md`

5. **If the note already exists**, update it by appending new items to the relevant sections. Use the Edit tool to add bullets under the appropriate headings. Don't duplicate items already present.

6. **Show the user** a brief summary of what was recorded.

## Rules

- Keep bullet points concise — one line per item
- Use wiki-links for service names and decision/review references: `[[decision-name]]`, `[[service-name]]`
- Don't fabricate work — only record what actually happened in this session
- If no context is available from the conversation, ask the user what they worked on

## Demo tags

Tag work items with `#demo` categories so sprint demos can be filtered:

- `#demo/highlight` — significant feature, release, or milestone worth showcasing
- `#demo/minor` — small fix or improvement worth mentioning briefly
- `#demo/internal` — tooling, infra, or DX work that benefits the team but isn't user-facing

Every "What I worked on" bullet should have a demo tag. Use your judgment:
- Releases, new features, POC completions → `#demo/highlight`
- Bug fixes, small enhancements → `#demo/minor`
- Architecture docs, dev tooling, CI/CD, skills → `#demo/internal`
