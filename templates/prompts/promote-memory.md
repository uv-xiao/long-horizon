# Promote Memory Prompt

## Hard Constraints

- Promote stable factual knowledge only.
- Include source artifact refs and stale conditions.
- Do not encode executable workflow policy as memory.

## Sequential Phases

1. Extract the stable lesson from run evidence.
2. Verify the lesson is reusable and not task-local.
3. Write the configured memory file.
4. Record source refs, scope, stale conditions, validation, and rollback.

## Output Artifacts

- Updated memory file.
- Deposition review artifact.
