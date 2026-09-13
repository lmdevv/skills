---
name: throwaway
description: Write scratch, one-shot, or sandbox code under /tmp instead of the repo. Use when the user asks for throwaway code, a sandbox, a one-off test, or says the work should not land in the project.
disable-model-invocation: true
user-invocable: true
metadata:
  opencode/autoinvoke: false
---

# Throwaway

This code is disposable. Treat it as a sandbox, not a project.

## Rules

- Put every generated file under `/tmp`. Use a fresh dir like `/tmp/throwaway-<short-name>/`.
- Do not write into the workspace, git repo, or home config unless the user names a path.
- Do not commit, open a PR, or tidy the code for later reuse.
- Skip production polish. No extra docs, tests, or abstractions unless they are required to run the experiment.
- Prefer one file or a tiny script. Run it once, report the result, leave it.

## After

Give the user the exact path. Do not copy anything into the repo unless they ask.
