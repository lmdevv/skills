---
name: commit
description: "Use when the user asks the agent to commit changes."
disable-model-invocation: true
user-invocable: true
metadata:
  opencode/autoinvoke: false
---

# Commit changes

## Quick commit

If you made changes in this conversation thread, you already know what changed. Run a quick verification, then commit directly:

1. `git status --short` - quick sanity check.
2. `git diff --stat` - confirm the change set matches what you expect.
3. Stage all relevant files (`git add -A` or specific files).
4. Commit with conventional title, optional bullet body, and **Co-authored-by** trailer.
5. `git status --short` - verify clean result.

Do **not** re-read every file or diff line-by-line. You already made the changes.

## Commit format

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

## Co-authors

When you made changes, add separate trailers for the model and coding tool. Add a trailer for each other model that contributed. Do not put harness or thinking metadata in brackets inside an author name.

```text
Co-authored-by: <provider>/<model-name> <noreply@<provider-domain>>
Co-authored-by: <coding-tool> <noreply@<tool-domain>>
```

Use runtime context first, then environment variables such as `PI_PROVIDER` and `PI_MODEL`. Omit unknown identities or email addresses. Do not invent them. Omit thinking level, it is not an author. Deduplicate trailers.

Derive the model name from its ID:

- Normalize the provider prefix (e.g. `opencode-go` -> `opencode`, `anthropic` -> `anthropic`, `openai` -> `openai`).
- Strip trailing deployment qualifiers (e.g. `claude-sonnet-4-20250514` -> `claude-sonnet-4`).
- Examples: `opencode/glm-5.1`, `anthropic/claude-sonnet-4`, `openai/gpt-5.5`.

Example with known co-author addresses:

```text
Co-authored-by: anthropic/claude-sonnet-4 <noreply@anthropic.com>
Co-authored-by: Claude Code <noreply@anthropic.com>
```
