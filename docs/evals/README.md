# Long-Horizon Evals

This directory documents end-to-end eval examples for the template. These evals
are stricter than unit or system tests: each eval creates a fresh target git
repository under `/tmp/evals`, launches a new Codex session inside that target
repo with `codex exec --dangerously-bypass-approvals-and-sandbox`, and then
verifies the resulting long-horizon artifacts from the outside.

The eval target is intentionally not this template repository. The target agent
must install and use the template in the target repo, then leave reports,
ledgers, process state, and commits that a human reviewer can inspect.

## Current Examples

- [Calculator](calculator.md): implement a safe expression calculator while
  exercising installation, task setup, process creation, mailbox messages,
  observer intervention, notification, evaluation, report GUI manifest, report
  generation, and final git commit evidence.

## Standard Flow

Each eval should provide:

1. a script under `scripts/evals/`;
2. a fresh target git repo under `/tmp/evals/<name>/target-repo`;
3. a generated Codex prompt artifact;
4. an external verifier that checks target repo behavior and long-horizon
   evidence;
5. a documentation page under `docs/evals/` naming review artifacts.

The verifier is the acceptance boundary. A Codex final message is useful
context, but it is not proof by itself.
