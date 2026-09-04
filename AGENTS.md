# Skills

This repo hosts public skills on GitHub.

When asked to add or update a skill, edit its directory here. 

In order to add or edit any skill, you first have to read unslop skill, that gives you the guidelines on how to write for any skill in this project. Remember, less word = better

## Skill format

Use the Agent Skills `SKILL.md` format so skills work across Codex, OpenCode, Cursor, and Claude Code.

Every skill must start with this frontmatter:

```yaml
---
name: skill-name
description: Say what the skill does and when the user should invoke it.
disable-model-invocation: true
user-invocable: true
metadata:
  opencode/autoinvoke: false
---
```

Keep automatic invocation off by default. `disable-model-invocation` applies to Claude Code and Cursor. `metadata.opencode/autoinvoke` applies to OpenCode. `user-invocable` keeps the skill available for explicit user invocation in Claude Code. The other harnesses expose skills for explicit invocation by default.

Every skill must also include `agents/openai.yaml`:

```yaml
policy:
  allow_implicit_invocation: false
```

Codex reads that file to disable implicit invocation. Do not put harness-specific behavior in the skill body. Keep descriptions short because harnesses advertise them before loading the full instructions.
