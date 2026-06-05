# Long-Horizon Template Repository Rules

These rules apply to this repository while evolving the long-horizon template itself. They are maintainer rules, not part of the template that gets installed into target repositories unless an install skill explicitly copies a separate template file.

## Documentation Boundaries

- `README.md` is the public product/design document. It should describe the template, architecture, phases, mechanisms, components, and public source rationale.
- Do not put run logs, research acquisition notes, temporary review documents, or private scratch paths in `README.md`.
- Do not mention gitignored local paths in public product files such as `README.md`. Public product files may cite upstream project names, article titles, or public URLs, but not ignored workspace locations.
- Maintainer-only rules may name standard private auth/log locations when needed to define agent behavior.
- Temporary research material, downloaded articles, cloned repos, review transcripts, and brain-simulated review logs belong in ignored local work areas such as the repository `tmp/` tree.
- If evidence from a private work area informs public docs, summarize the evidence in public terms and keep the raw path in the local work log.

## Template vs Repository-Maintainer Artifacts

- Template artifacts are files intended to be copied or installed into target repositories.
- Repository-maintainer artifacts are rules, skills, logs, and changelogs used to evolve this template repo.
- Keep those two artifact classes separate. A rule or skill for maintaining this repo must not be described as an installable template component unless it is explicitly designed and reviewed for target repos.

## Evolution Workflow

- Before changing the template design, read the repo-local skill `.agents/skills/evolve-long-horizon-template/SKILL.md`.
- First update or consult maintainer rules/skills when the problem is about how the template should evolve.
- Use ignored local logs for evidence collection and simulated reviews.
- Public documentation should contain the final architectural result and concise rationale, not the full working transcript.
- When a commit/PR-sized change materially changes the template, update `CHANGELOG.md`. The change log tracks commit/PR work, not releases, and should record public-facing design changes rather than private scratch evidence.

## GitHub CLI Workflow

- GitHub operations should use the repo-local `.agents` skills and shared `.agents/lib/github` procedures.
- Before running `gh`, follow `.agents/rules/github-cli.md`.
- Prefer local GitHub CLI auth/config in `.gh/` or `tmp/gh/` by exporting `GH_CONFIG_DIR`.
- If neither local auth directory exists, stop and tell the user how to create one instead of falling back silently to global auth.
- If `gh` is unavailable, stop and give install/setup commands.

## README Quality Bar

- The README should stay structured by phase, mechanism, and component.
- Avoid flat feature piles.
- Avoid overlapping concepts: goal contract, plan, logging, versioning, review, memory, and reporting each need a clear owner.
- Treat Codex `/goal` as an agent substrate adapter, not as the whole system.
- Treat logging as a repo-maintainer and runtime substrate, not as a README section full of raw notes.
