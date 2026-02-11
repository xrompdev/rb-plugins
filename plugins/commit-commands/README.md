# commit-commands

Streamline your git workflow with commands for committing, pushing, and creating pull requests. Commit messages are generated without co-author attribution.

## Commands

| Command | Description |
|---------|-------------|
| `/commit` | Stage files and create a commit with an AI-generated message |
| `/commit-push-pr` | Commit, push, and open a PR in one step |
| `/clean_gone` | Remove local branches deleted from the remote, including worktrees |

### `/commit`

Analyzes your current changes and recent commit history to generate a commit message matching your repository's style. Stages and commits in a single operation.

### `/commit-push-pr`

Full workflow: creates a branch (if on main), commits, pushes, and opens a pull request using `gh pr create`.

### `/clean_gone`

Finds local branches marked as `[gone]` (deleted on remote), removes associated worktrees, and deletes the branches.

## Requirements

- Git must be installed and configured
- For `/commit-push-pr`: GitHub CLI (`gh`) must be installed and authenticated
