---
name: sync-reviews
description: Sync recent PR reviews from GitHub into the Obsidian vault (backfill missing review notes)
argument-hint: "[repo] [--days N]"
allowed-tools:
  - Bash
  - Write
  - Read
---

# Sync PR Reviews to Vault

Pull recent PR review activity from GitHub and create vault notes for any reviews not already captured. Use this to backfill reviews done by the scheduled routine or manual reviews.

## Instructions

1. **Parse arguments**:
   - `repo`: Optional repo (default: detect from current directory, or use `responsibid-server`)
   - `--days N`: How far back to look (default: 7)

2. **List recently closed/merged PRs** that were reviewed:

```bash
gh pr list --repo {owner/repo} --state merged --json number,title,author,url,mergedAt,closedAt --limit 50
```

Also check open PRs that have been reviewed:

```bash
gh pr list --repo {owner/repo} --state open --json number,title,author,url --limit 50
```

3. **For each PR, check if it has reviews**:

```bash
gh pr view {number} --repo {owner/repo} --json reviews --jq '.reviews[] | {state, author: .author.login, submittedAt: .submittedAt}'
```

Filter to PRs reviewed within the last N days.

4. **Check which reviews are already in the vault**:

List existing files in `/home/xromp/obsidian/responsibid-brain/Reviews/`. If `{PR#}-*.md` already exists, skip that PR.

5. **For missing reviews, get the diff and create vault notes**:

```bash
gh pr diff {number} --repo {owner/repo}
gh pr view {number} --repo {owner/repo} --json title,body,author,files,additions,deletions
```

6. **Write review notes** using the same format as `/brain:patrol` step 7e.

7. **Report** how many reviews were synced:

```
Synced X review notes to vault (skipped Y already captured)
```

## Service Mapping

Map changed file paths to services:
- `apps/graphql-server/` → `server-graphql`
- `apps/gateway/` → `server-gateway`
- `apps/payment/` → `server-payment`
- `apps/orchestrator/` → `server-orchestrator`
- `apps/projector/` → `server-projector`
- `apps/reactor/` → `server-reactor`
- `apps/notification/` → `server-notification`
- `apps/pdf-service/` → `server-pdf-service`
- `apps/temporal-worker/` → `server-temporal-worker`
- `apps/queue/` → `server-queue`
