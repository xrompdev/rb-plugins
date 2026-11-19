---
name: patrol
description: Review open PRs and capture results into the Obsidian vault
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
  - Agent
---

# PR Patrol — Review + Vault Capture

Review open (non-draft) PRs, walk me through them one at a time in a question wizard (approve, approve with light comments, or go through each comment to post or ignore), submit only what I confirm on the final summary, and save each review to the Obsidian vault.

## Steps 1–4: Run the prep script

Patrol runs over several repos at once. The repos are the checkout names in `$ARGUMENTS` when given (e.g. `/brain:patrol responsibid-php`), otherwise these five: `responsibid-server`, `responsibid-php`, `subscriptions`, `terraform-infra`, `crewcal`. `responsibid-client-v2` is left out by default; review it only when named in `$ARGUMENTS`. Each lives at `~/projects/<name>`; that folder is the PR's **repo dir** for every later step. Accept an `$ARGUMENTS` name only when it is letters, digits, `.`, `_` and `-` (no `/`, no spaces) and `~/projects/<name>/.git` exists; report any other name in one line and leave it out of the run.

Run the prep script once per repo, all at the same time, each from its repo dir. List the repos as literal words in the `for` line (zsh does not split a variable):

```bash
for r in responsibid-server responsibid-php subscriptions terraform-infra crewcal; do
  rm -f <scratchpad>/patrol-prep-$r.json <scratchpad>/patrol-prep-$r.err
  (cd ~/projects/$r 2> <scratchpad>/patrol-prep-$r.err && python3 -I /home/xromp/.claude/plugins/cache/rb-plugins/brain/0.8.2/scripts/patrol_prep.py > <scratchpad>/patrol-prep-$r.json 2> <scratchpad>/patrol-prep-$r.err) &
done; wait
```

Replace `<scratchpad>` with your scratchpad directory, then read `patrol-prep-<name>.json` for each repo in the run (go by the repo list, not by the files present). A repo whose prep failed (its `.json` is missing or empty; its `.err` says why) is reported in one line, e.g. `subscriptions: prep failed (gh auth)`, and the run goes on with the others. A PR in a file's `failed` list (its `reason` names the `gh` call that failed) is reported the same way, e.g. `responsibid-server#2931: prep failed: gh api repos/…/files: HTTP 404`, and left for me to review by hand. Each file's `repo` field is the GitHub `owner/name`. An entry with `files_truncated` true has more than 3,000 changed files, so its `services` and code facts may miss paths: say so in its overview. PR numbers repeat across repos, so name a PR `<repo dir name>#<number>` everywhere in the run. The script applies these rules in code, per repo:

- Lists every open PR (`--limit 1000`; the `gh` default of 30 silently drops the rest).
- Filters out drafts, Dependabot PRs (author `dependabot`, `dependabot[bot]` or `app/dependabot`), and my own PRs (`xrompdev`).
- Skips a PR **I** have approved. Approvals from other reviewers do NOT count.
- Compares my latest conversation comment or review with the latest commit. If I never commented, it's a `review`. If the author pushed since then, it's a `re-review`. Otherwise it's skipped.
- For each PR to review: reads the linked issues, takes their `- [ ]` requirements, collects my earlier comments on a re-review, works out the services and code facts, and fetches the PR head into `refs/patrol/<number>`.

The Jev pre-pass then adds a `jev` block to each PR:

| Field | Meaning | How to use it |
|---|---|---|
| `risk` | Jev's own score from Trivial to High | An input only. Set depth from the entry's top-level `risk` (below), which can be higher |
| `lessons_to_apply` | `LESSONS.md` lessons whose trigger Jev judged likely to match (p ≥ 0.3) | Apply these lessons. Skip the others unless the diff clearly matches one Jev missed |
| `adrs_to_open` | ADRs whose area Jev judged the diff touches | Open these ADRs, and only these, unless the diff clearly touches another one |
| `conditional` | p for Replica reads (`read_after_write`), Money arithmetic (`money`), Event and workflow safety (`event_or_workflow`), Tenant scoping and authorization (`tenant_or_auth`), Public API contract (`public_contract`) and a destructive migration (`destructive_migration`, which the 5c DB schema row checks closely) | Apply the 5d criterion when p ≥ 0.3. For `tenant_or_auth` ≥ 0.3, check every new or changed query, resolver and guard in the diff against the 5c Tenant scoping row, not a sample. These say *where* the risk is; `risk` says how much |
| `requirements` | Each linked-issue requirement, `covered` / `verify` / `not covered` | Check `verify` items in the code. Confirm a `not covered` item in the code before raising it. If the PR body says it is only *part of* the issue, items it doesn't claim are not concerns |
| `earlier_comments` | On a re-review, whether each of my comments looks addressed | Spot-check `covered` items. Check `verify` and `not covered` items in the code |

Code facts decide the rest: `touches_connect`, `touches_db_schema`, `context_md`, `environment_ts_changed` and `services`.

Each entry also carries:

- `risk`: the level that sets review depth. It is the higher of Jev's level and the rule-based minimums in the script's `RISK_FLOORS` (money, tenant scoping or auth, a destructive migration and event or workflow history make a PR at least High; a public contract, Connect, any schema or migration file and `environment.ts` make it at least Medium). Path rules always count; Jev-question rules count only when Jev is confident (p ≥ 0.8). `raised_by` names the rules that decided the final level when it is above Jev's level, or every rule at the floor when Jev gave no level, and `floor_rules` lists every rule that matched. Depth: a Trivial or Low PR gets a quick read; High gets every criterion checked closely. Without Jev the level reads `at least <level>` or `unknown`, and the PR gets the full checklist anyway.
- `other_reviewers`: `changes_requested_by` (other reviewers whose latest review still requests changes), `approved_by`, and `unresolved_threads` other people started (humans and bots like Qodo). The review agent reads each open block and thread: a real one it agrees with goes into its concerns (citing the reviewer); one already fixed at the head it notes as fixed.
- `checks`: the head commit's CI, as `failing` and `pending` check names. A failing check is not a review concern by itself (the author sees it), but a PR with failing or pending checks cannot be approved on Submit (6e).
- `head_sha`: the commit prep fetched into `refs/patrol/<number>`, the only head the agent may review (5a) and the SHA its report is checked against (step 6).
- `last_reviewed_commit` on a re-review: the commit my last review was on. The agent reviews `git -C <repo dir> diff <last_reviewed_commit> refs/patrol/<number>`; when `force_pushed` is true (that commit is no longer an ancestor of the head, or is gone), it reviews the whole PR diff instead, not commit messages, and reads every review and thread posted since.

If `jev` is null (no key, or `jev_error` is set), review that PR against the full checklist: every lesson in `LESSONS.md` and every ADR title. Tell me in one line before the reviews start, e.g. `Jev unavailable (HTTPError) for responsibid-server#3230, responsibid-client-v2#3229; reviewing with the full checklist.`

Jev's verdicts are leads, not findings. Never raise a concern on a Jev verdict alone.

## Step 5: Review (Light)

### 5a. Review every PR in parallel

Hand each PR in `to_review` to its own background agent, launching them all in one message so they run at the same time. Give each agent:

- Its PR entry from the prep JSON, pasted into the agent prompt. Do not write it to a file for the agent to read: the jev-guard hook screens tool output, reads the lessons as instructions aimed at an agent, and tells the agent to ignore them.
- Its repo dir and GitHub `owner/name`.
- The repo's `REVIEW.md` from the base branch (`git -C <repo dir> show origin/main:REVIEW.md`), pasted into the prompt for the same reason, when the repo has one. Read it from the base, not the PR head, so a PR that edits `REVIEW.md` is not reviewed against its own rules. When the repo has none, say so in the prompt.
- The path to this file, with an instruction to read sections 5b–5d for the criteria and rules.
- Its `head_sha`, and the rule that `refs/patrol/<number>` (that SHA) is the only head of the PR: it must not read `origin/<branch>`, a local branch or any other ref for the PR. Agents can't fetch, so those can still hold history from before a force-push.
- The rule that it is read-only. It must not approve, comment, write files, check out branches, or fetch. It reads code with `git -C <repo dir> show refs/patrol/<number>:<path>` and `gh pr diff <number> -R <owner/name>` (GitHub refuses a diff over 20,000 lines; then it uses `git -C <repo dir> diff origin/<base branch>...refs/patrol/<number>`, the base branch from `gh pr view <number> -R <owner/name> --json baseRefName`), and opens `CONTEXT.md`, ADR and other files under its repo dir.
- What to return: the head SHA it reviewed, verdict (Approve / Approve with light comments / Needs review), a one-line summary, a two-or-three-sentence overview, linked issue, key changes, follow-ups, and whether `environment.ts` changed.
- Concerns, each already verified in the code and returned as a **ready-to-post draft**: `path:line` inside a diff hunk (or "conversation"), its tier (Blocking or Nit, per 5b) with the rule it falls under, the concrete failure scenario for a Blocking one, and the exact comment text written to the 6a rules. Include the path to this file so the agent can read 6a.

Agents read `CONTEXT-MAP.md`, plus the `context_md` files and `adrs_to_open` from their entry, as they need them. Do not wait for all of them: start Step 6 as soon as the first agent returns.

### 5b. How to review

- Verify a concern before reporting it. Read code at the PR head with `git -C <repo dir> show refs/patrol/<number>:<path>`. Check that a "missing" test, guard, or call site is not elsewhere in the PR or the codebase.
- Say so when a concern comes from reading the code and was not run.
- A clean PR is a valid result. Do not invent concerns.
- **Follow-ups are only for work outside this PR's scope.** A defect in the diff (a replica read, an unscoped query, a retry loop, an event with no consumer, a bad default) is always a concern, never a follow-up.
- Give every concern exactly one tier, **Blocking** or **Nit**. There is no third tier.
  - **With a `REVIEW.md`**, its Standards, Spec and Replay safety sections set the tiers. Name the `REVIEW.md` rule each concern falls under.
  - **Without one**, Blocking means a correctness defect with a concrete failure scenario: wrong money, a lost or duplicated write or side effect, a cross-company read, a broken retry, a wrong or terminal status, a dead-end flow, a security hole. Everything else is a Nit.
  - Patrol's own criteria (5c, 5d) do not add tiers. A finding from them is Blocking only when it meets the Blocking bar above.
- A Blocking concern states its failure scenario: the input or state, and what the user or the data ends up with. If you cannot write one, it is a Nit.
- Before calling a concern a Nit, check it against the Blocking bar. A concern that loses a write, sends nothing, or leaves a wrong status is Blocking, however small the fix.
- A Blocking concern never comes back with an Approve or Approve-with-light-comments verdict.
- Skip anything Biome or tsc already enforces.
- Before raising a concern, read the whole linked-issue thread and the earlier review threads on the PR. Do not ask to undo something the author changed on purpose, a fix another reviewer asked for, or a decision the product owner has since reversed.
- On a re-review, check each earlier concern in the code at the head. An author reply saying it is fixed is not evidence.
- Do not raise commit-message or commit-body wording, and do not ask for "an integration test" without naming the case it must cover. Both get ignored.
- Do not ask to rename anything (a variable, function, file, field or type), not even as a Nit. This holds over any naming Nit a `REVIEW.md` Code Style section would allow. A name is a concern only when the code behind it is wrong: then raise the behaviour, not the name. The exception is a **contract name**, one that is stored or called by name outside the PR's code, so changing it later breaks running systems: an event type, a projection's name string (the name passed to the projection, not its class name), a Temporal workflow, signal, query or activity name, a RabbitMQ exchange, routing key or queue, a job name, a GraphQL or Connect field or route path, a database column, an environment variable or an aggregate type. A contract name the PR renames, or introduces in a form that breaks a stated rule (the 5d camelCase rule for Connect params, the glossary term for an existing concept), is a concern.
- When the run ends, the main session deletes every `refs/patrol/*` ref in each repo dir: `git -C <repo dir> for-each-ref --format='%(refname)' refs/patrol/ | xargs -r -n1 git -C <repo dir> update-ref -d`, one command per repo.

### 5c. Criteria for every PR

Review ONLY for the criteria in 5c and 5d:

| Criterion | What to check |
|-----------|---------------|
| **DB schema** | Are migrations safe? No destructive changes without migration steps? |
| **REVIEW.md** | When the repo has one, apply its Standards, Spec and Replay safety sections in full: they come first, and the rows below add to them. |
| **Proper types** | No `any`, no loose typing where existing types exist |
| **Existing patterns** | Follows conventions already in the codebase. Find the sibling component, handler or rule that already does the same job (a validation helper the sibling form calls, an existing hook, a rollup rule) and compare: does the new code reuse it or match its behaviour? |
| **No unnecessary novelty** | No new libraries or architectural patterns when existing ones work |
| **Test coverage** | New logic or changed behavior must have corresponding tests. Flag new services, resolvers, or utility functions that lack spec files. Modified branches (new if/else, error paths, edge cases) should be covered. For Connect service changes (`apps/connect/`), integration tests are **required** — flag if only unit tests are present or tests are missing entirely. |
| **Gateway-only access** | All public endpoints MUST go through the gateway. NO direct external calls to server or payment services. Flag any endpoint that bypasses the gateway. |
| **Infra change reminder** | If the diff includes changes to any `environment.ts` file, leave a PR comment: "This PR changes `environment.ts` — don't forget to raise a corresponding change on infra." |
| **Requirement match** | Does the diff do what the PR body and linked issue ask? Flag acceptance criteria the diff does not cover, behaviour that contradicts the issue, and changes outside the stated scope. A PR with no linked issue and no stated intent is not a concern by itself — record it under Follow-ups. |
| **Retro lessons** | Apply each lesson in the PR's `jev.lessons_to_apply` (all of `LESSONS.md` when `jev` is null). Name the lesson in the concern. |
| **Tenant scoping and authorization** | Every new or changed query and mutation is scoped to the caller's company, including field resolvers and nested reads. New endpoints and resolvers have a guard, and use role vs scope the way the authorization ADRs describe. |
| **Failure and retry** | For each new or changed handler, workflow, side effect or client call: is a retry safe to repeat (no reopened record, no double write)? Does each failure end in a defined outcome, not a misleading message (a 502 shown as "nothing saved") or a loop resending a refused request? Can a new side effect (a publish, a webhook, telemetry) block or fail the user's request? |
| **Probe-review probes** | Apply the probes in `~/.claude/skills/probe-review/SKILL.md` §2 that `LESSONS.md` now points to: Sibling flow, Docs vs code, Repeat refusals, Outside claims and Fixture values. Skip Commit bodies. |

### 5d. Criteria that apply only when the diff touches the area

| Applies when the diff touches | Criterion | What to check |
|-------------------------------|-----------|---------------|
| An app with a `CONTEXT.md` | **Domain language and invariants** | Behaviour matches the glossary in that `CONTEXT.md`, and no stated invariant is broken. Naming differences are not raised, except on contract names (5b). |
| An area governed by an ADR | **ADR compliance** | The change does not contradict the ADR. If it deliberately does, the PR must say so and update or supersede the ADR. |
| A read after a write, or a read that decides a write (`conditional.read_after_write`) | **Replica reads** | A read that must see current data runs on the writer: inside the same `$transaction` as the write, or as a conditional write / `FOR UPDATE`. That covers check-then-act reads: validation, duplicate checks, status and auth state (a deactivated user, an existing record). Reads outside it can be served by a stale replica. |
| Money (`conditional.money`) | **Money arithmetic** | Amounts are in cents (integers), not rounded dollars. Rounding can't turn a small amount into zero or leave a 1-cent mismatch that dead-ends a charge. Every handler that adds to or subtracts from a total is updated (refunds, force-refunds, pending reservations). |
| Client UI code (`responsibid-client-v2`, plugins) | **UI safety** | New menus and controls are keyboard-operable. Sensitive inputs (passwords, card data) are masked in Datadog session replay. Sanitized HTML keeps link attributes safe (`rel="noopener"`, no `opener`). |
| CI workflows, nx or lint config | **CI config** | Caches are keyed on every input that changes the result (tool versions, config). Triggers and path filters cover every changed path. A stacked branch is current with its parent. |
| `apps/connect/`, or a GraphQL schema, webhook or event payload (`conditional.public_contract`) | **Public API contract** | No breaking change to a response shape, param, or status code. OpenAPI snapshot regenerated. Sort and filter params are camelCase. No Prisma or domain logic in Connect. |
| Event-sourced code or Temporal workflows | **Event and workflow safety** | Existing event shapes are not changed in place (new version or new event instead). Projections handle the new events, and a newly published event has a consumer or the PR says which one comes next. Workflow code stays deterministic — no clock, randomness, or I/O outside activities. |

## Step 6: Decide each PR with me, one at a time

Run the wizard as reviews come in. When a review agent returns, take me through that PR (6b–6c) straight away. Don't wait for the other agents.

Before a returned review enters the wizard, compare the head SHA it says it reviewed with the entry's `head_sha`. This is one string comparison, not a code re-check. On a mismatch (or no SHA), re-launch that agent once with the SHA restated. If the second report still doesn't match, show the PR as "Needs review" with the reason `stale read: reviewed <sha>, head <head_sha>`, with options **Leave** or **Review it myself later**, and never post its drafts.

The agent's drafts are the wizard's content. Present them as returned. **Do not re-check the code, re-run `git`/`gh`, or redraft between questions**: the agent already verified each concern, and every extra step is time I spend waiting. Only touch a draft to fix wording that breaks a 6a rule, without any tool calls.

- After I finish a PR, move on to the next PR whose review has already returned. Take PRs that other reviewers have already approved (`other_reviewers.approved_by`) first, since they can merge soonest; otherwise in the order they finished.
- If none is ready, say which reviews are still running and wait for the next one to return.
- If a review returns while I'm still answering questions about another PR, queue it. Never interrupt a PR halfway through.
- An agent that fails or returns nothing still gets its turn: show the PR with verdict "Needs review" and the reason, with options **Leave** or **Review it myself later**.

Show the final summary and submit step (6d) only after every PR has been decided. The wizard only collects my decisions. **Nothing is approved or posted until I choose Submit in 6d.**

Give each PR a verdict from its review:

- **Approve**: no concerns.
- **Approve with light comments**: every concern is a Nit (5b). The drafts open with `Non-blocking:`.
- **Needs review**: at least one concern should block approval.

### 6a. Draft the comments

Write one comment per concern, covering the concerns only — follow-ups stay in the vault note.

- Inline wherever the concern is about specific code: give each draft the file path and a line on the new side of the diff. The line must fall inside a diff hunk — pick the changed line closest to the problem (for removed code, the line that replaced it).
- A conversation comment only when the concern has no line: a merge gate, a test that does not exist, an unmet requirement about the PR as a whole.
- Short. One or two points per PR, a sentence or two each.
- State the concern directly, with the concern as the first words of the comment.
- Casual, the way a teammate writes. End each point with a concrete question or ask about the code.
- I am one reviewer among several. Do not mention my approval, and do not ask the author to ping me or do anything for me.
- Hedge what was not verified ("from my read").
- Never mention Claude, AI, or automation.

For an approve-with-light-comments PR, use the same inline-first rules: one inline comment per minor point, each opening with `Non-blocking:`. A point about a line outside the diff (a stale docblock, an untouched doc file) goes on the nearest changed line and names the file or spot it means. Only a point with no line at all goes in a conversation comment, also opening with `Non-blocking:`. Do not add an `LGTM.` comment; the approval says that.

```
Non-blocking: <the concern>. <question or ask>?
```

The rules above on length, tone, hedging and not mentioning automation apply to these too.

### 6b. One question per PR

Ask about each PR with a single-select `AskUserQuestion`, starting the moment its review is ready. Wait for my answer before moving on to the next PR. Put a progress note in the question, e.g. `(2 of 5 · 2 reviews still running)`.

- **header**: a short repo name and the number, at most 12 characters, e.g. `server#2975`, `client#812`, `php#3301`, `subs#90`, `infra#41`, `crewcal#57`
- **question**: three lines.
  - `<repo dir name>#<number>: <one-line summary of what it does>`
  - `Overview: <two or three sentences: what changed, the risk level, and how many concerns there are>`. The risk level is the entry's `risk.level`, followed by `(raised by <raised_by>)` when that list is not empty.
  - `Verdict: <Approve | Approve with light comments | Needs review>`
  - When other reviewers have something open, a fourth line: `Open from others: changes requested by <logins>; <n> unresolved threads (<authors>)`.
  - When `checks` has failing or pending names, a line: `CI: failing <names>; running <names> — approval will be held on Submit unless it's green by then`.
- **options**, with the option matching the verdict first and labelled `(Recommended)`:

| Option | When to offer it | What happens on Submit |
|---|---|---|
| **Approve** | only when no draft is blocking. Never `(Recommended)` while another reviewer's changes-requested or an unresolved thread they started is open | Silent approval (6e) |
| **Approve + light comments** | only when there are drafts | The drafts are posted, then the PR gets a silent approval. Put the drafts, each with its `path:line` or "conversation", in the option's `preview` |
| **Proceed to review** | always, except for a clean PR with no drafts | Go to 6c |

If I answer with free text through "Other", follow it. For example, "skip" leaves the PR untouched, and an edit changes the drafts.

### 6c. Proceed to review: one question per comment

Go through every draft for the PR, blocking and `Non-blocking:` alike, as single-select questions. **Put all of the PR's comments in one `AskUserQuestion` call** (it takes up to four questions), so I answer them together as one form. Use more calls only for a PR with more than four comments, four at a time.

- **header**: `#<number> <i>/<n>` (the repo is in 6b's header and the question line, so it stays within 12 characters)
- **question**: the concern in one line, then its `path:line` or "conversation".
- **options**:
  - **Post**: put the exact comment text in the `preview`.
  - **Ignore**: the comment is dropped.

A free-text answer is an edit: apply it, and treat the comment as Post.

After the last comment:

- If at least one comment is set to Post, the PR outcome is **comment, no approval**. Never approve a PR that I sent through review with blocking comments.
- If every comment is set to Ignore, ask one more question for the PR: **Leave without approval** (Recommended) or **Approve**.

### 6d. Final summary and submit

After the last PR, show a summary table with one row per PR: `<repo dir name>#<number>`, title, decision (approve / approve + N light comments / N comments, no approval / leave / skip), and the `path:line` of each comment to post. Then ask one `AskUserQuestion`:

- **Submit**: carry out every decision (6e), then report each PR's result with the review or comment URL.
- **Change a PR**: ask which PR, run 6b–6c again for it, then show the summary again.
- **Cancel**: post nothing and approve nothing.

### 6e. Posting on Submit

Run every command in this step from the PR's repo dir (`cd <repo dir> && ...`): `gh` resolves `{owner}/{repo}` and `git` resolves `refs/patrol/<number>` from the current folder, so a command run elsewhere acts on the wrong repo. For each PR, first run the gate, which reads the PR fresh:

```bash
python3 -I /home/xromp/.claude/plugins/cache/rb-plugins/brain/0.8.2/scripts/patrol_prep.py --gate <number> "$(git rev-parse refs/patrol/<number>)"
```

- If the gate exits non-zero or prints no JSON, or `state` is `UNKNOWN` (`hold` says why), post nothing and approve nothing for that PR, and list it as "gate failed" with the reason and its drafts, so I can submit it by hand.
- If `state` is merged or closed, post nothing, and list it in the result as "merged before submit" along with any blocking drafts it lost, so I can raise them as a follow-up.
- Otherwise post its comments. Then, when the decision was to approve, approve only if `approve` is true. If it is false, do not approve: list the PR as "approval held" with each `hold` reason. A moved head means commits nobody reviewed; the next patrol picks the PR up as a re-review (prep compares my last review's commit with the head). Failing or running checks are not retried by a later patrol when the head stays put, so for those print the command to approve once CI is green, gated again: `cd <repo dir> && python3 -I /home/xromp/.claude/plugins/cache/rb-plugins/brain/0.8.2/scripts/patrol_prep.py --gate <number> <reviewed sha> | jq -e .approve && gh pr review <number> --approve`. Never approve past a hold, even if I chose Approve in the wizard.

Build each request with `jq` as shown below and pipe it straight in, one command per PR. Don't build arguments in a shell variable for a loop to expand: the shell is zsh, which doesn't split `$var` into words, so the command breaks silently.

Silent approval has NO body, NO comment flag and NO review message — zero text on the PR:

```bash
gh pr review <number> --approve
```

Inline comments go in one review per PR, with event `COMMENT` and no review body. Anchor them to the commit that was reviewed (`refs/patrol/<number>`), not to the current head, so the line numbers match the diff I saw. If the head has moved since then, say so in the result:

```bash
jq -n --arg sha "$(git rev-parse refs/patrol/<number>)" '{
  commit_id: $sha,
  event: "COMMENT",
  comments: [{path: "<file path>", line: <line>, side: "RIGHT", body: "<comment>"}]
}' | gh api -X POST repos/{owner}/{repo}/pulls/<number>/reviews --input -
```

Conversation comments:

```bash
gh pr comment <number> --body-file -
```

The review response's URL points at the whole review, not at each comment, and 7f matches concerns by each comment's own URL. So after posting the `COMMENT` review, read its comments with the `id` the response returned and record each `html_url` (a `#discussion_r…` link) against the concern with the same `path` and `line`:

```bash
gh api repos/{owner}/{repo}/pulls/<number>/reviews/<review id>/comments --jq '.[] | {path, line: (.line // .original_line), html_url}'
```

`gh pr comment` prints the conversation comment's URL; record that one as is.

Never put comments in an `APPROVE` or `REQUEST_CHANGES` review. For approve + light comments, post the `COMMENT` review first, then run the silent approval separately.

### Global Rules

- Never post a review comment I have not seen and approved in this session.
- The `environment.ts` infra reminder is the only comment posted without asking. Check existing comments first and never post it twice on a PR.

## Step 7: Capture to Vault

After the 6d submit step, whether I chose Submit or Cancel, write a review note for each reviewed PR to the Obsidian vault. Record what I decided, not only what the review found.

### 7a. Get today's date

```bash
date +%Y-%m-%d
```

### 7b. Determine filename

Format: `{PR#}-{kebab-case-slug}.md` derived from the PR title. Compare `repo:` values by the part after the last `/` (older notes may hold `owner/name`), and treat a note with no `repo:` as the same repo. If that file already exists for a different repo, use `{PR#}-{repo dir name}-{kebab-case-slug}.md` instead.
Example: PR #342 "fix invoice total calculation" → `342-fix-invoice-total-calculation.md`

### 7c. Check if already captured

Check if `/home/xromp/obsidian/responsibid-brain/Reviews/{filename}` already exists with the same `repo:`. If it does and this is a re-review after new commits (Step 3), append a `## Re-review {YYYY-MM-DD}` section with which earlier concerns were addressed and any new ones, and update `status`. Also set each earlier posted concern's `outcome` in the Review section from what the review agent found at the head (5b checks every earlier concern there) and the comment's thread: `fixed` (changed at the head; tick its checkbox), `disputed` (the author pushed back and I let it go), `open` (still there, no reply yet; 7f keeps checking it), or `moot` (the code it was on is gone for another reason). `unaddressed` is only for a PR that merged or closed with the point untouched, which 7f decides. An ignored concern keeps `outcome:: open`: it was never posted. Leave `risk`, `risk_jev`, `risk_score`, `risk_raised_by`, `blocking`, `nits`, `posted` and `ignored` as the first review set them: they record how well the pre-review risk (Jev's score and each minimum rule) predicted what the review found, so later runs can check whether the score and each rule are worth trusting. Otherwise skip vault capture for this PR.

### 7d. Determine repo and services

Map the repo to known service names: `responsibid-server`, `responsibid-client-v2`, `responsibid-php`, `terraform-infra`, `subscriptions`, `crewcal`.

Take the affected services from the PR's `services` field in the prep JSON. The script maps paths with this table; keep the two in sync:
- `apps/server/` → `server-graphql`
- `apps/connect/` → `server-connect`
- `apps/shortener/` → `server-shortener`
- `apps/queue-dispatcher/` → `server-queue-dispatcher`
- `apps/zapier-app/` → `server-zapier-app`
- `apps/gateway/` → `server-gateway`
- `apps/payment/` → `server-payment`
- `apps/orchestrator/` → `server-orchestrator`
- `apps/projector/` → `server-projector`
- `apps/reactor/` → `server-reactor`
- `apps/notification/` → `server-notification`
- `apps/pdf-service/` → `server-pdf-service`
- `apps/temporal-worker/` → `server-temporal-worker`
- `apps/queue/` → `server-queue`

### 7e. Write the review note

Write to `/home/xromp/obsidian/responsibid-brain/Reviews/{filename}`:

```markdown
---
type: review
date: {YYYY-MM-DD}
pr: {PR number}
repo: {repo dir name, e.g. responsibid-server}
author: {PR author login}
status: {approved|needs-review}
risk: {the entry's risk.level, lowercased: trivial|low|medium|high|at least <level>|unknown}
risk_jev: {risk.jev_level lowercased, or null}
risk_score: {jev.risk.score, or null}
risk_raised_by: {risk.raised_by as a YAML list, or []}
blocking: {number of Blocking concerns the review found, posted or not}
nits: {number of Nit concerns the review found, posted or not}
posted: {number of concerns posted, edited or not}
ignored: {number of concerns I ignored in the wizard}
---

## Summary

{1-2 sentence summary of what the PR does, derived from title and diff}

Linked issue: {#number and title, or "none"}

## Key changes

- {Notable changes from the diff — what files/modules were touched and why}

## Review

- [ ] {Blocking | Nit}: {the concern, with `path:line`; for Blocking, the failure scenario} [rule:: {what raised it: a `REVIEW.md` rule, a lesson's first words, or the 5c/5d criterion}] [source:: {patrol, or the reviewer or bot whose open thread it came from}] [call:: {posted | edited | ignored | not posted}] [url:: {the posted comment's URL, or none}] [outcome:: open]
- [ ] {Next concern, same fields}

`call` is what happened to the draft, decided after 6e: `posted` (posted as drafted), `edited` (posted after I changed it), `ignored` (I chose Ignore in 6c), or `not posted` (I chose Post or Approve + light comments but nothing went up: Cancel, gate failed, merged before Submit, or Approve chosen in 6b with drafts dropped, or "skip"). `posted:` in the frontmatter counts `posted` and `edited`; `ignored:` counts `ignored`. `outcome` starts as `open` and is set on a re-review (7c) or by 7f. Together they tell a good catch from a nit later: a posted concern that ends `fixed` was a catch (more so when Blocking); one I `ignored`, or that ends `disputed` or `dropped`, was noise; `unaddressed` is neither until I look.

If no concerns: replace the checkboxes with "No issues found — approved.", or "No issues found — approval held: <hold reasons>." when the gate held it.

## Follow-ups

- {Any follow-up work identified, or "None"}

## PR comment

{The drafted comments for a flagged PR, each with its `path:line` or "conversation". Omit this section for an approved PR.}
```

For posted comments, put the text as posted and its URL in this section. List comments I chose to ignore under `Ignored`. On Cancel, keep the drafts and mark them `not posted`.

Use `status: approved` when the PR was approved on Submit, with or without light comments. A held approval is `status: needs-review`, with the hold reasons under Follow-ups. Otherwise use `status: needs-review`: these notes have unchecked boxes in the Review section for you to work through in Obsidian.

### 7f. Settle open outcomes

A re-review only happens while I have not approved, so posted Nits on a PR I approved, and anything on a PR that merged before the next run, would never get an outcome. Before the summary, for each repo in this run, find its review notes (`repo:` matches) with a concern line that has `call:: posted` or `call:: edited`, a `url::` holding `#discussion_r` (an inline comment; conversation comments have no thread state, so they stay `open` and are not queried), and no `settled::` field. For each such PR, from its repo dir:

```bash
cd <repo dir> && python3 -I /home/xromp/.claude/plugins/cache/rb-plugins/brain/0.8.2/scripts/patrol_prep.py --outcomes <number>
```

- If it exits non-zero, prints no JSON or returns `error`, change nothing for that PR and list it in the summary with the error.
- Match each concern to a `comments` entry by its URL. Leave a concern with no match as it is (if `threads_truncated` is true, say so in the summary).
- Write the entry's `outcome` into the concern line, with these readings:
  - `fixed`: the line changed under the comment, or someone other than me resolved the thread. Tick the checkbox. A rebase that rewrites the hunk reads the same way: a known false positive.
  - `replied`: the author answered and the line did not change. Read `author_last_reply` and write `fixed` when it says the point was handled (changed elsewhere, reworded, will do in this PR) or `disputed` when it pushes back (intended, out of scope, won't do).
  - `dropped`: I resolved my own thread, letting the point go.
  - `unaddressed`: the PR merged or closed and nothing happened.
  - `open`: nothing yet; leave it.
- When `state` is `MERGED` or `CLOSED`, add `[settled:: {YYYY-MM-DD}]` to every concern line of that PR, so later runs stop checking it. While the PR is open, a written outcome can still change on the next run.
- In the summary, list each outcome this step wrote, one line each (`<repo>#<number> <path:line>: <outcome>` plus, for one read from a reply, its first words), so I can correct a misread. A fix made somewhere the thread cannot see can still read `unaddressed`; I correct those by hand.

### 7g. Summary

End with a brief summary of the run:

```
## Patrol Summary

- **Repos**: R (and any whose prep failed)
- **Prep failed** (left for review by hand): F
- **Reviewed**: X PRs
- **Approved**: Y (Z with light comments)
- **Commented, not approved**: C
- **Approval held** (head moved or CI not green): H
- **Left or skipped in the wizard**: L
- **Skipped** (already reviewed): N
- **Vault notes written**: M (in Reviews/)
- **Outcomes written** (7f): S (fixed / disputed / dropped / unaddressed), listed one per line
```
