# Long-Horizon Evals

This directory documents end-to-end eval examples for the template. These evals
are stricter than unit or system tests: each eval creates a fresh target git
repository under repo-local `./tmp/evals`, launches a new Codex session inside
that target repo with `codex exec --dangerously-bypass-approvals-and-sandbox`,
and then verifies the resulting long-horizon artifacts from the outside.

The eval target is intentionally not this template repository. The target agent
must install and use the template in the target repo, then leave reports,
ledgers, process state, process chat/transcript artifacts, captured external
process logs, and commits that a human reviewer can inspect.

## Current Examples

- [Calculator](calculator.md): implement a safe expression calculator while
  exercising installation, task setup, process creation, mailbox messages,
  observer intervention, notification, evaluation, report GUI manifest, report
  generation, and final git commit evidence.

## Standard Flow

Each eval should provide:

1. a script under `scripts/evals/`;
2. a fresh target git repo under `./tmp/evals/<name>/target-repo`;
3. a generated Codex prompt artifact;
4. an external verifier that checks target repo behavior and long-horizon
   evidence;
5. a documentation page under `docs/evals/` naming review artifacts.
6. process-log artifacts under `./tmp/evals/<name>/artifacts/process-logs/`
   for every external process the eval launcher opens, including prompt,
   command, stdout, stderr, run metadata, and final agent message when the
   process is an agent session;
7. target-run chat artifacts under
   `.long-horizon/goals/<goal>/runs/<run>/artifacts/process-chats/` for every
   long-horizon process modeled by the eval.

The verifier is the acceptance boundary. A Codex final message is useful
context, but it is not proof by itself.
