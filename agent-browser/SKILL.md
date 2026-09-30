---
name: agent-browser
description: Run separate Chrome browsers for automation, testing, or scraping on Linux, headlessly or in a Hyprland scratchpad.
disable-model-invocation: true
user-invocable: true
metadata:
  opencode/autoinvoke: false
---

# Agent browser

Use [scripts/browser.py](scripts/browser.py) to give each agent its own Chrome DevTools session. This separates browser data. It does not sandbox the agent's Linux account.

## Start

Resolve `B` below to this skill's `scripts/browser.py`. Use system Chromium or Chrome, Python 3, and Node.js with npx. The launcher fetches a pinned Chrome DevTools CLI, which controls its MCP server through a private local socket. It does not open a debugging TCP port.

Choose the mode from the task. Over SSH, default to headless even if desktop variables exist.

```sh
python3 "$B" start --mode headless --output-dir /absolute/task/output
python3 "$B" start --mode desktop --workspace magic --output-dir /absolute/task/output
```

Run one start command. Save the returned session ID as `S`. Desktop mode needs a running Hyprland session with the Lua window-rule API. On this user's machine, Super+Z toggles `special:magic`. Launching must not reveal it or switch focus.

Use disposable profiles unless the user selects persistence. Add `--profile NAME` for a dedicated persistent profile. Each profile allows one active session. Never copy or attach to the user's everyday profile. Separate profiles can still change the same website account.

Read [references/setup.md](references/setup.md) for NixOS dependencies, extensions, persistent login setup, and desktop limits.

## Work

```sh
python3 "$B" tool "$S" list_pages
python3 "$B" tool "$S" navigate_page 1 --url https://example.com
python3 "$B" tool "$S" take_snapshot 1
python3 "$B" tool "$S" click 1 ELEMENT_UID
```

Use returned page IDs and fresh snapshot UIDs. Get command arguments with `tool "$S" COMMAND --help`. Use browser tools for input, never global mouse or keyboard injection. Keep every call on this session. Do not use the upstream CLI's default session or change its connection options.

## Authentication and handoff

Prefer Bitwarden's matching-site autofill when its extension is installed and unlocked. Use its normal UI. Do not read vault internals, export secrets, or obtain a Bitwarden CLI session. Autofilled passwords and authenticated cookies remain accessible to browser control.

Pause if vault unlock, MFA, passkey verification, or another login step needs the user. In headless mode, explain the blocker and wait. There is no remote viewer or automatic switch to desktop mode.

```sh
python3 "$B" pause "$S"
python3 "$B" resume "$S"
```

Pause before inviting manual input. The pause command waits for the current tool call and blocks further wrapper calls. Watching alone need not pause. Resume only after the user hands control back. Do not capture authentication screens or filled credentials.

## Finish

```sh
python3 "$B" stop "$S"
python3 "$B" status
```

Stop when finished or abandoning the task. Keep requested downloads and screenshots in the output directory. Stop deletes disposable browser data and session records, but preserves named profiles and output files. Never use `pkill chrome` or delete another session's files.

Sessions expire after four hours, including pauses. Set `--ttl SECONDS` at startup for longer work. A closed or failed session needs `stop` to clear its records. Report the mode, profile policy, handoff instructions, and any remaining authentication blocker.
