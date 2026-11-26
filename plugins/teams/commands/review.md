---
description: Start a review team — three diff-reviewers (standards, spec, security) that challenge each other's findings
argument-hint: "[base branch or PR number] (default: origin/main)"
---

# Review team

Review the current branch with an agent team before it is pushed. You are the **lead**: you collect the findings that survive cross-examination.

## 1. Scope

1. Resolve the base: a PR number in `$ARGUMENTS` → its base branch via `gh pr view`; a branch name → that branch; empty → `origin/main`.
2. Find the spec: the PR description, or the issue it names, or ask the user.
3. List the changed files with `git diff --stat <base>...HEAD`.

## 2. Spawn

Create the team with three `diff-reviewer` teammates, one per lens: **standards**, **spec**, **security**. Give each the base, the changed-file list and the spec text.

## 3. Collect

Each finding needs a concrete failure scenario to survive. Drop findings the other reviewers refute, and merge duplicates across lenses.

## Done

The team is done when all three reviewers have reported. Give the user the surviving findings ranked by severity, each with file:line, lens and failure scenario, followed by the list of files every reviewer checked. Then shut the team down.
