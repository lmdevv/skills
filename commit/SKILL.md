---
name: commit
description: "Use when the user asks the agent to commit changes."
---

# Commit Changes

## Quick Commit

If you made changes in this conversation thread, you already know what changed. Run a quick verification, then commit directly:

1. `git status --short` - quick sanity check.
2. `git diff --stat` - confirm the change set matches what you expect.
3. Stage all relevant files (`git add -A` or specific files).
4. Commit with conventional title, optional bullet body, and **Co-authored-by** trailer.
5. `git status --short` - verify clean result.

Do **not** re-read every file or diff line-by-line. You already made the changes.

## Commit Format

**Title:**

```text
type(scope): summary
```

- `type`: feat, fix, chore, docs, test, refactor, migrate, update, perf, build, ci
- `scope`: affected area/package/domain
- `summary`: imperative present tense, lowercase, no period

**Body (optional):** use bullets only, for changes >100 lines or notable impact.

```text
- explain the main behavior or implementation change.
- explain any important risk, migration, or follow-up.
```

**Co-author trailer (when you made the changes):**

```text
Co-authored-by: <provider>/<model-name> [harness: <harness>; thinking: <level>] <noreply@<provider>.ai>
```

Always try to include provider and model, then harness, then thinking level when available. Determine them from your runtime context first, then environment variables such as `PI_PROVIDER`, `PI_MODEL`, `PI_REASONING_LEVEL`, or harness-specific equivalents. Omit unavailable fields rather than inventing them. Use a provider-appropriate noreply domain.

Derive slug from the current model ID:

- Normalize the provider prefix (e.g. `opencode-go` -> `opencode`, `anthropic` -> `anthropic`, `openai` -> `openai`).
- Strip trailing deployment qualifiers (e.g. `claude-sonnet-4-20250514` -> `claude-sonnet-4`).
- Examples: `opencode/glm-5.1`, `anthropic/claude-sonnet-4`, `openai/gpt-5.5`.
- Use `noreply@<provider>.ai` (or `.com` for providers like Google).
