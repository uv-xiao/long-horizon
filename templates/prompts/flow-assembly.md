# Flow Assembly Prompt

## Hard Constraints

- Do not mutate active run boards directly.
- Flow files define allowed states and gates; transition tools mutate run
  boards only after validation.

## Sequential Phases

1. Read the approved goal contract and task setup.
2. Choose workflow states, allowed transitions, and terminal states.
3. Declare artifact gates, check gates, human gates, and wait/join gates.
4. Declare parent/child/fork/join topology and process ownership.
5. Declare observer and reporter roles.
6. Split responsibilities between native-agent features and template runtime.
7. Write readable flow plan plus structured flow data.
8. Validate with `python -m long_horizon validate --root .` where applicable.

## Review Gate

Challenge hidden branch switches, missing join criteria, weak candidate
selection evals, and native/runtime responsibility overlap.
