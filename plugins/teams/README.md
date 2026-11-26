# teams

Four agent-team clusters for Claude Code. Each command makes your session the team lead and spawns teammates from this plugin's agents.

## Setup

1. Install the plugin:

   ```
   claude plugin marketplace add xrompdev/rb-plugins   # skip if already added
   claude plugin marketplace update rb-plugins
   claude plugin install teams@rb-plugins
   ```

2. Turn on agent teams. They are experimental and off by default, and a plugin can't switch them on for you. Add this to `~/.claude/settings.json` (merge it into an existing `env` block if you have one):

   ```json
   { "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
   ```

   Or for one shell only: `export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

3. Run `/reload-plugins` in a running session, or start a new one, so the `/teams:*` commands appear. The settings-file flag takes effect without a restart; a shell `export` needs a new session.

With the flag on, Claude may also run ordinary delegated work as named teammates, not only inside these commands. Teams don't start in `claude -p` or Agent SDK sessions.

## Usage

| Command | Teammates | Use for |
|---|---|---|
| `/teams:feature <issue>` | `server-dev`, `client-dev`, `php-legacy` (when legacy is involved), `retro-observer` | Features that span server, client-v2 and PHP |
| `/teams:debug <symptom>` | 3× `hypothesis-hunter`, `retro-observer` | Bugs with several plausible causes |
| `/teams:review [base\|PR]` | 3× `diff-reviewer` (standards, spec, security), `retro-observer` | Adversarial review before pushing |
| `/teams:api <issue>` | 2× `pm` (advocate, skeptic), `qa-engineer`, 1–5× `api-engineer`, `retro-observer` | Public (Connect) API changes: justify scope, write acceptance criteria, build, verify against the dev lane |
| `/teams:reconcile [--dry-run]` | none | Turn problems that recur across team retros into edits to these agents and commands (draft PR) |

A session leads one team at a time. To run two clusters at once, start them in separate sessions.

Each teammate is a full Claude Code session, so a team costs several times a single session. Use a single session for work inside one file or a strict sequence of steps.

## Components

- **Agents** `server-dev`, `client-dev`, `php-legacy`, `hypothesis-hunter`, `diff-reviewer`, `pm`, `api-engineer`, `qa-engineer`, `retro-observer`
- **Commands** `feature`, `debug`, `review`, `api`, `reconcile`

In `/teams:api` the session is the team lead engineer: it spawns every teammate (teammates cannot spawn teammates), pauses for your confirmation of the PMs' plan, and its QA requests hit the dev lane, which reads and writes **staging** data. Export a staging token as `RB_TOKEN` before the verify phase. Dev lane problems are handled by the lead with the `dev-lane-troubleshoot` skill when it is installed; other environment blockers come straight to you. Ask "how are the agents doing?" at any point to get `retro-observer`'s performance snapshot: verdict and tuning advice for each agent.

Every agent reads the repo's `CLAUDE.md` first, and `~/obsidian/responsibid-brain/Retros/LESSONS.md` when it exists.

## Self-improvement loop

Every team runs a `retro-observer` that logs the run and saves a retro to `~/obsidian/responsibid-brain/Retros/<date>-teams-<team>-<slug>.md`, ending in a `## Tuning` table of proposed prompt rules. `/teams:reconcile` reads the unreconciled retros, applies each rule shown by two or more runs to the agent or command file in a draft PR, sends general rules to `Retros/LESSONS.md`, keeps single-run problems on a watch list, and writes `Retros/<date>-teams-reconcile.md`. It also grades each run's work once its PRs close (first-push CI, findings accepted in `Reviews/Received/`, debug fixes that didn't hold) and pins each miss on the agent that should have caught it. It promotes blockers seen in two runs to preflight checks in `Areas/ResponsiBid/services/teams/blockers-log.md`, which every team command runs before spawning. Run it by hand or from cron, e.g. every three days:

```
0 9 */3 * * cd ~/obsidian/responsibid-brain && claude -p /teams:reconcile --permission-mode bypassPermissions
```
