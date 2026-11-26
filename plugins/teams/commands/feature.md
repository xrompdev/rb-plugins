---
description: Start a feature team — server-dev and client-dev, plus php-legacy when legacy behaviour is involved
argument-hint: "<issue number, URL or feature description>"
---

# Feature team

Build the feature in `$ARGUMENTS` with an agent team. You are the **lead**: you own the task list and the final summary; teammates own the code in their repo.

## 1. Scope

1. Read the issue or description. If it is a GitHub issue, fetch it with `gh issue view`.
2. Locate the repos the feature touches (`responsibid-server`, `responsibid-client-v2`, `responsibid-php`) under the working directory or `~/projects`. Ask the user for any path you cannot find.
3. Decide whether legacy PHP behaviour is involved (a port, or PHP code that reads or writes the same data). Include `php-legacy` only then.
4. Write the task list: one task per teammate, each ending on that teammate's completion criterion. Put the legacy inventory and the contract agreement first; implementation tasks depend on them.

## 2. Spawn

Create the team with one teammate per role, using the plugin's agent types: `server-dev`, `client-dev`, and `php-legacy` when included. Give each teammate its repo path, the base branch, the feature branch name, and the issue text.

Each teammate works in its own repo, so their edits never share a file.

## 3. Run

- Hold implementation until `server-dev` and `client-dev` have both confirmed the contract.
- When a teammate reports done, check its report against its task's completion criterion before marking the task complete.

## Done

The team is done when every task is complete and you have given the user: the agreed contract, per-repo changes with the commands run and their results, and every item a teammate could not check. Then shut the team down.
