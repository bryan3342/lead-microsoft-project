# lead-project

Instructions for Claude, both locally (Claude Code) and on GitHub (the workflows in `.github/workflows/`).

## Conventions

- Issue and PR titles are `label:short description`, with no space after the colon, and each item carries exactly one label.
- Every change lands through a pull request; nothing is pushed straight to `main`.
- Keep PRs small and single-concern, and describe what changed and why.
- No AI attribution in commits, PRs or docs: no `Co-Authored-By` trailers, session links or "Generated with" footers.

## Claude on GitHub

- `claude.yml`: replies when the owner or a collaborator writes `@claude` in an issue, PR or review comment. Read-only.
- `claude-pr-review.yml`: reviews each new PR and each human push to it, commits bug and code smell fixes to the PR branch, and posts a summary. It never merges, approves or touches other branches. Add the `no-claude` label to a PR to skip it.

Both authenticate with the `CLAUDE_CODE_OAUTH_TOKEN` repository secret and need the Claude GitHub App installed on the repo.
