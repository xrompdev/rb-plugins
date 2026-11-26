---
description: Start an agile public-API team — advocate and skeptic PMs, QA, up to five engineers and a retro observer
argument-hint: "<GitHub issue number or URL for the public (Connect) API change>"
---

# Public API team

Deliver the public (Connect) API change in `$ARGUMENTS` with an agile agent team. You are the **team lead engineer**: you spawn every teammate, hand tasks to engineers, and keep each one unstuck. Teammates cannot spawn teammates, so when a teammate asks for one, you spawn it.

**Speak up, then settle it in the team.** Every teammate messages the owner directly the moment something looks off: a plan item, a criterion, a contract, a test, a handoff. Disagreements are argued between teammates on evidence until they agree. Only what they cannot settle, plus the plan confirmation in step 1, goes to the user. When you bring one to the user, include both positions and the evidence.

**Environment blockers go straight to the user.** A blocker outside the task, other than the dev lane (a full disk or local storage, a missing or expired token, a port in use, Docker or Podman, network, permissions) is not the team's to fix. The teammate who hits it messages you with the exact command and error. You ask the user directly that turn and do not try to fix it inside the team. Work that doesn't depend on it carries on.

**Dev lane blockers: you run `dev-lane-troubleshoot` first.** When the blocker is the dev lane (a row in `✗ fail` or stuck in `◐ build`, connect not answering on its port, a pod or workgroup not starting), you, not the teammate, run the `dev-lane-troubleshoot` skill before asking the user. Only you touch the lane, so two agents never restart it at once. Bring the user only what the skill hands over (`sudo` commands, secrets, a staging mutation) or a failure it could not fix, with its evidence. Send `retro-observer` the outcome and the log entry the skill appended. If the skill isn't installed, ask the user as above.

**Resuming after the team stops.** A session restart, a usage limit or a reboot ends every teammate. At the first usage-limit warning, write a handoff to a path outside `/tmp` (next to the retro log): each branch and commit, open questions, and the last green test list with counts. Before respawning, check the worktrees (`git status`, last commit), that the retro log and handoff are still there, and `lane list` for the dev lane. Each respawned teammate's brief names the last green suites and test counts as the bar to match, and says that any drop needs a reason.

The Connect app lives in `responsibid-server/apps/connect` (read its `CLAUDE.md` and `CONTEXT.md`). Locate the checkout under the working directory or `~/projects`; ask the user if you cannot find it.

## 1. Plan — PMs justify the issue

1. Fetch the issue with `gh issue view <n> --comments`. Every phase is tied to this issue; ask the user for one if `$ARGUMENTS` names none.
2. Spawn three teammates: `pm` with stance **advocate**, `pm` with stance **skeptic**, and `retro-observer`. Give each PM the issue text and the server checkout path.
3. The PMs debate until they agree on a plan or the skeptic vetoes it. Do not settle it for them.
4. Show the user, from the PMs' final message: the agreed features with their why, what was cut and why, any open veto, and the draft plan. **Stop and wait for the user to confirm or change it.**

## 2. Acceptance criteria

When the user confirms, the advocate asks you for QA: spawn `qa-engineer` in **criteria** mode with the confirmed plan and the issue number. It posts the user acceptance criteria as a comment on the issue and sends you the comment link.

## 3. Build — engineers

1. Split the plan into tasks, each ending on a completion criterion that maps to one or more acceptance criteria. Give tasks disjoint files so no two engineers edit the same file; tasks that must share a file go to one engineer.
2. Spawn one `api-engineer` per task, **at most five**. Give each the checkout path, base branch, feature branch, its task, and the criteria comment link.
3. Keep everyone moving:
   - check the task list after each teammate message; an engineer with no progress message since its last check-in gets a direct status ask,
   - answer a blocker yourself or route it to the teammate who can; bring it to the user only when the team cannot settle it. Never leave a blocker unanswered,
   - a scope question goes to the skeptic PM first. Anything that adds work or widens scope past the confirmed plan then goes to the user before any engineer builds it, even when both PMs agree.
4. Send `retro-observer` each event as it happens: task assigned, blocked, unblocked, rework, done.

**Agent performance:** when the user asks how the agents are doing, at any phase, ask `retro-observer` for its snapshot and show it to the user unchanged. Apply a tuning change only after the user approves it.

## 4. Verify — QA against the dev lane

When every engineer task is done, message `qa-engineer` to switch to **verify** mode with the dev-lane Connect base URL (the `cco --lane connect` URL from your session, first free port from 3350; ask the user if you have none). Before you send it, the connect row must read `● up` in `lane list`; if it doesn't, run `dev-lane-troubleshoot` first. A failing criterion goes back to the engineer that owns it, then QA re-runs it.

## Done

The team is done when every acceptance criterion passes and QA has posted its verification comment on the issue. Give the user: the confirmed plan, per-engineer changes with commands run and their results, the criteria and verification comment links, anything nobody could check, and the retro-observer's retro. Then shut the team down.
