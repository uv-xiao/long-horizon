---
name: promote-rule
description: Promote a recurring repository rule into `.agents/rules/` with deposition evidence.
---

# Promote Rule

## Purpose

Use this when a run reveals a durable rule that future agents should follow.

## Scope

Promote stable repository policy into `.agents/rules/` rather than a skill or
task artifact.

## Required Reads

- run evidence for the repeated failure or successful constraint;
- existing `.agents/rules/`;
- `AGENTS.md`;
- relevant policy decisions.

## Allowed Writes

- `.agents/rules/<rule>.md`;
- deposition review artifacts;
- rollback notes.

## Workflow

1. Identify the repeated failure or successful constraint.
2. Decide whether it belongs in `.agents/rules/` instead of a skill.
3. Patch the smallest relevant rule file.
4. Record deposition evidence under `.long-horizon/artifacts/deposition/`.
5. Include rollback instructions and examples of when the rule does not apply.

## Produced Artifacts

- rule file or rule patch;
- deposition evidence;
- validation and counterexample notes.

## Commands

Use runtime promotion commands when available, or patch the rule file and record
equivalent evidence manually.

## Failure Handling

Block promotion when the rule is task-specific, conflicts with higher-priority
instructions, or weakens safety gates without approval.

## Completion Evidence

The rule exists, changed files are named, validation is recorded, and reports
show the promotion event.

## Example

Promote a rule requiring source-backed merge repair only after a run shows a
merge failure was mishandled without that rule.
