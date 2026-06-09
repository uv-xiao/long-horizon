# Long-Horizon Template Agent Entry

Use this directory for repository-local agent rules, skills, and shared procedures.

## Required Rules

- Follow the root `AGENTS.md` for public documentation boundaries and template evolution rules.
- Use `.agents/skills/evolve-long-horizon-template/SKILL.md` before changing template architecture, installable skills, README, changelog, STATUS, or maintainer evidence logs.
- Use `.agents/rules/github-cli.md` before any GitHub CLI operation.

## GitHub Workflows

GitHub skills live under `.agents/skills/` and share procedures from `.agents/lib/github/`.

Available GitHub-related skills:

- `checkout-pr`
- `clean-branches`
- `create-issue`
- `fix-issue`
- `fix-pr`
- `git-commit`
- `github-pr`
- `review-pr`
