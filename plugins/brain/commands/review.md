---
name: review
description: Capture a PR review into the Obsidian vault
argument-hint: "<PR# or URL> [repo]"
allowed-tools:
  - Write
  - Read
  - Bash
  - AskUserQuestion
---

# Capture PR Review

Write a PR review note to the ResponsiBid Obsidian vault.

## Instructions

1. **Parse arguments** to determine:
   - **PR identifier**: A PR number or GitHub URL
   - **Repo**: Optional repo name (defaults to detecting from current git directory)

2. If no PR is specified, ask the user which PR they reviewed.

3. **Get PR details from GitHub** using the `gh` CLI:

```bash
gh pr view {PR#} --repo {owner/repo} --json title,body,author,number,files,additions,deletions,baseRefName,headRefName
```

If no repo is specified, try the current directory's remote:
```bash
gh pr view {PR#} --json title,body,author,number,files,additions,deletions
```

4. **Determine the repo name** from the remote URL or user input. Map to the known repos: `responsibid-php`, `responsibid-client-v2`, `responsibid-server`, `terraform-infra`, `subscriptions`.

5. **Extract review context** from:
   - The PR diff and changed files
   - The current conversation (if the user just finished reviewing)
   - Ask the user for their review summary if not available from context

6. **Determine the filename**: `{PR#}-{short-slug}.md`. Example: PR #342 about payment webhook → `342-payment-webhook.md`.

7. **Write the review note** to `/home/xromp/obsidian/responsibid-brain/Reviews/{filename}`:

```markdown
---
type: review
date: {YYYY-MM-DD}
pr: {PR#}
repo: {repo-name}
author: {PR author}
status: {approved|needs-review}
---

## Summary

{1-3 sentence summary of what the PR does}

## Key changes

- {Notable changes, architectural decisions, new patterns introduced}

## Review

- [ ] {Each concern as a checkbox — specific issue with file path and line number if possible}
- [ ] {Next concern}

If no concerns: replace the checkboxes with "No issues found — approved."

## Follow-ups

- {Any follow-up work identified, or "None"}
```

8. **Show the user** the file path and summary.

## Rules

- Use today's date: `date +%Y-%m-%d`
- Default status to `approved` unless the user indicates otherwise
- Use wiki-links for service references in the body
- Keep the summary focused on what matters for future reference, not the full diff
- If `gh` is not available or fails, ask the user for PR details manually
