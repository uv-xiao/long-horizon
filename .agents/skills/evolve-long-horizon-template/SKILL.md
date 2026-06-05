---
name: evolve-long-horizon-template
description: Use when changing this repository's long-horizon template design, maintainer rules, installable skills, architecture, README, changelog, or evidence logs.
---

# Evolve Long-Horizon Template

Use this skill for changes to the template repository itself. Do not use it as an installable target-repo skill.

## Core Rule

Keep public template design, installable template artifacts, and maintainer work logs separate.

## Workflow

1. **Classify the change.**
   - Public design: README, changelog, installable templates, installable skills.
   - Maintainer process: AGENTS.md, repo-local skills, private review logs.
   - Raw evidence: downloaded articles, cloned repos, transcripts, temporary analysis.

2. **Keep ignored paths out of public files.**
   - Public docs may cite project names, article titles, and public URLs.
   - Public docs must not cite ignored local paths.
   - Store raw path evidence in ignored local logs under `tmp/`.

3. **Use local review logs for design stress tests.**
   - Write simulated reviews, source-reading notes, and iteration evidence in an ignored local work area under `tmp/`.
   - Public docs should summarize the result, not link to temporary logs.

4. **Refactor by ownership.**
   - Phase: lifecycle step.
   - Mechanism: reusable substrate across phases.
   - Component: installable skill, template, hook, adapter, or view.
   - If a concept overlaps, choose one owner and reference it from the others.

5. **Update public docs only after the architecture is stable.**
   - README should state the final structured design and concise rationale.
   - Changelog should record commit/PR-sized public design changes, not releases.
   - Do not include research acquisition status in README.

## Review Checklist

- No ignored local paths appear in public product files such as README.
- Temporary review logs are not under public documentation directories.
- README remains organized by phase, mechanism, and component.
- Logging details needed for this repo's evolution live in AGENTS.md or this skill, not README.
- Installable template components are not confused with maintainer-only rules.
