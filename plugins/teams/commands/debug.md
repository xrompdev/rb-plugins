---
description: Start a debug team — three hypothesis-hunters that each own one explanation and attack the others
argument-hint: "<symptom, error, or bug report>"
---

# Debug team

Find the root cause of `$ARGUMENTS` with an agent team of competing hypotheses. You are the **lead**: you form the hypotheses, judge the evidence, and propose the fix.

## 1. Hypotheses

1. Pin down the symptom: what was expected, what happened, for which record, account or request, and since when.
2. Write three hypotheses that predict **different** observations. Two hypotheses that predict the same thing are one hypothesis; replace one of them.

## 2. Spawn

Before spawning, read the Preflight table in `~/obsidian/responsibid-brain/Areas/ResponsiBid/services/teams/blockers-log.md` and run each check that matches the repos this team touches. Fix or report a failure first, and put the known fixes for a teammate's repo in its brief.

Create the team with three `hypothesis-hunter` teammates, one hypothesis each. Give every hunter the symptom, all three hypotheses, the repo paths, and which environment it may query read-only.

Also spawn `retro-observer`, team `debug`, with the symptom and the three hypotheses.

**Agent performance:** send `retro-observer` each event as it happens (hypothesis assigned, challenged, refuted or confirmed, new hypotheses, evidence a hunter had to ask you for). When the user asks how the agents are doing, ask `retro-observer` for its snapshot and show it unchanged. Apply a tuning change only after the user approves it.

## 3. Judge

- Let the hunters challenge each other. A hypothesis survives when no hunter can produce an observation it fails to explain.
- When every hypothesis is refuted, write new ones from the evidence gathered and reassign.

## Done

The team is done when one hypothesis is confirmed by evidence that rules out the others. Give the user: the root cause with file:line, the evidence chain, why each other hypothesis was refuted, the proposed fix at the shared code path every caller routes through, the callers it covers, and the path of `retro-observer`'s retro. Wait for the retro before you shut the team down; make the fix only after the user agrees.
