---
description: Reconcile team retros — turn problems that recur across /teams runs into edits to this plugin's agents and commands
argument-hint: "[--dry-run]"
---

# Reconcile team retros

Read the retros every `/teams` run saved in the vault, find the problems that keep coming back, and fix them where they start: the agent or command prompt in this plugin. Runs unattended every three days from cron, and can also be run by hand. This command makes no team.

Vault: `~/obsidian/responsibid-brain`. Plugin source: `github.com/xrompdev/rb-plugins`, `plugins/teams/`.

With `--dry-run`, do steps 1–3 and print the note from step 5 without writing, committing or pushing anything.

## 1. Collect

1. Pending retros: `Retros/*-teams-*.md`, excluding `*-teams-reconcile.md`, whose frontmatter has no `reconciled:` key or `reconciled: false`.
2. None pending? Say `No new team retros since the last reconcile.` and stop. Write nothing.
3. Read the latest `Retros/*-teams-reconcile.md`, if any, for its `## Watching` list.

## 1b. Grade quality

A run's process can look clean while its work wasn't. Grade the work from what happened to it after the team called it done.

For each `Retros/*-teams-*.md` with `quality: pending` (reconciled or not) and a non-empty `prs:` list:

1. Check each PR with `gh pr view <n> --repo <owner/repo> --json state,mergedAt,headRefName`. Any PR still open → leave `quality: pending` and grade it next time.
2. **First-push CI:** `gh run list --repo <owner/repo> --branch <headRefName> --json conclusion,createdAt,name --limit 50`, and take the earliest run of each workflow. Red → one miss.
3. **Caught after done:** read `~/obsidian/responsibid-brain/Reviews/Received/<n>-*.md` for each PR. Every row with an accepted (fixed) verdict is one miss. Rows that were deferred, skipped or already addressed are not misses.
4. **Debug runs:** also check the fix held. Search the vault (`Retros/`, `Daily/`, `Reviews/Received/`) and the issue's later comments for the same symptom coming back, or a finding saying the root cause was wrong. Either one counts as a miss with severity high.
5. **Attribute each miss** to the agent whose task or lens covered it: the `diff-reviewer` lens that should have flagged it, the engineer that owned the file, `hypothesis-hunter` or the lead for a wrong root cause, `qa-engineer` for a criterion that passed but shouldn't have. Turn it into a Tuning row (target, proposed rule, evidence = the received note's finding and its Mistake pattern) and add it to step 2's grouping like any other row.
6. Set `quality: <YYYY-MM-DD> — CI first push <green|red>, <n> caught after done` in the retro's frontmatter.

A run with no PR (`prs: []`) gets `quality: n/a`.

## 2. Group

From each pending retro take its `## Tuning` rows. Retros written before the Tuning section existed have none; take their `Went wrong` rows paired with the matching `Do better` item, and set the target yourself from which agent or step caused it.

Group rows that describe the same problem in different words, and fold in matching `Watching` items from the last reconcile. A group's **count** is the number of distinct retros that show it.

## 3. Decide

For each group:

- **Count ≥ 2, target in this plugin** → apply it (step 4).
- **Count ≥ 2, target `LESSONS`** → add or bump the line in `Retros/LESSONS.md` the way the `retro` skill's step 4b does: same rule already there → bump `(×N)` and add the links; new → one line under the matching heading.
- **Count 1** → `Watching`. Don't edit anything for a single run.
- **Already fixed:** the target file already has the rule (same meaning) → `Recurred despite rule`. Don't add it again; propose a stronger placement (an earlier step, the lead's handoff) in the note for the user, and don't apply that.

**Blockers.** Also read each pending retro's `## Blockers` table and the Known blockers in `~/obsidian/responsibid-brain/Areas/ResponsiBid/services/teams/blockers-log.md`. A blocker seen in 2 or more runs (`Runs seen` ≥ 2, or in 2 retros) with a fix that can be checked before the team starts becomes a row in that log's Preflight table: the scope, a check the lead can run, and what to do on failure. Edit the vault file directly; no PR. A blocker only the user can clear (`sudo`, a secret, an expired token) goes under `Needs you` with how often it hit and the time lost.

Never apply a rule that removes a check, a test, a confirmation with the user, or a safety rule, and never one that widens what an agent may do without asking (push, merge, write to prod or staging data). List those under `Needs you` instead.

## 4. Apply

1. Work in a fresh worktree off `origin/main` of the plugin source, never in `~/.claude/plugins/`:
   ```bash
   repo=~/.claude/plugins/marketplaces/rb-plugins
   wt=~/projects/worktree/rb-plugins-teams-reconcile-$(date +%Y-%m-%d)
   git -C "$repo" fetch origin
   git -C "$repo" worktree add "$wt" -b "teams/reconcile-$(date +%Y-%m-%d)" origin/main
   ```
   If the worktree or branch already exists, stop and put it under `Needs you`.
2. For each group to apply: add the proposed rule as one sentence at the step where it applies, in the file's own voice. Edit wording around it only as far as the new rule needs.
3. Bump the patch version in `plugins/teams/.claude-plugin/plugin.json`.
4. Commit once, message `fix(teams): reconcile retros <date>` with one body line per rule: the file, the rule, and the retro note names that show it.
5. Push with an explicit target (`git push -u origin teams/reconcile-<date>`) and open a **draft** PR with `gh pr create --draft`. The body lists each rule with its evidence links and the Watching list. Never merge it.

## 5. Record

Write `Retros/<YYYY-MM-DD>-teams-reconcile.md`:

```markdown
---
type: retro
date: YYYY-MM-DD
team: /teams:reconcile
retros: [<note names read>]
pr: <draft PR URL, or none>
tags: [retro, teams, reconcile]
---

## Applied
- <target> — <rule> — [[retro]], [[retro]]

## LESSONS
- <added or bumped line>

## Recurred despite rule
- <target> — <rule already there> — [[retro]] — proposed placement: <...>

## Watching
- <target> — <problem> — [[retro]]

## Quality
| Run | Team | First-push CI | Caught after done | Misses by agent |
|---|---|---|---|---|

Include every run graded this time, then one line comparing caught-after-done per run against the previous reconcile note's Quality table.

## Preflight added
- <scope> — <check> — [[retro]], [[retro]]

## Needs you
- <item and why it was not applied>
```

Leave a section out when it is empty. Then set `reconciled: <YYYY-MM-DD>` in the frontmatter of every retro you read. Don't commit the vault; its own flow does that.

## Done

Report: retros read, rules applied with the PR link, LESSONS lines changed, the Watching count, and every `Needs you` item.
