# Setup and limits

## Linux and NixOS

Use an installed browser first. `--browser /absolute/executable` overrides discovery. The launcher prefers Chromium and never downloads a browser binary or disables its sandbox.

If dependencies are missing on NixOS, use a development shell. Do not rebuild the user's system just to run this skill.

```sh
nix shell nixpkgs#python3 nixpkgs#nodejs nixpkgs#chromium
```

The launcher pins `chrome-devtools-mcp` to 1.10.1. Its CLI uses a separate UUID session for each agent. First use needs npm access. Native agent MCP configuration is unnecessary because the CLI talks to its own MCP server. The CLI's session option is version-sensitive. Retest concurrency before changing the pin.

`--output-dir` limits DevTools file tools. Add extension directories through `--extension`, which also grants the server access to those directories. This is not an operating-system sandbox. Usage statistics and CrUX URL reporting are disabled.

## Hyprland

Desktop mode requires the Lua API `hl.window_rule`. It was developed against this machine's Hyprland 0.56.2. Check API support, not just the version number. Older configurations need an adapted launcher or headless mode.

The launcher applies a named rule before Chrome opens. The rule matches the session's unique window class, places windows on `special:magic` silently, suppresses activation requests, and prevents initial focus. `--workspace NAME` selects another special workspace. It never adds keybindings or switches workspaces.

On this machine, Super+Z reveals or hides `magic`. Pause the agent before typing into its browser. Several agents may share this workspace while keeping separate processes and profiles.

Cleanup disables the named rule. Hyprland retains the inert entry until the next config reload. Do not reload the user's config for cleanup. A user-initiated config reload drops runtime rules, so stop desktop sessions before reloading. Browser-native prompts and extension windows need testing with the chosen browser. Do not promise that every possible popup preserves focus.

## Extensions and Bitwarden

To load an unpacked extension, pass its trusted local directory. Repeat for several extensions. The directory must contain `manifest.json`.

```sh
python3 "$B" start --mode desktop --profile personal-agent \
  --extension /absolute/path/to/extension --output-dir /absolute/task/output
```

The launcher uses the DevTools extension-install tool. Supply the extension path on each start when relying on this method. Installing an extension does not authenticate it.

For persistent Bitwarden setup, start a named desktop profile, pause it, and let the user install Bitwarden from its official store listing and sign in. Reuse that profile explicitly later. Vault locks, MFA, and website session expiry can still require intervention. Never save a master password in launch arguments, environment files, or the skill.

A disposable profile needs extension setup and authentication again. An unlocked extension in the user's everyday browser does not unlock this one. Headless extension support does not guarantee unattended password or passkey login. Pause when an interactive step is required.

## Storage and recovery

State lives under `$XDG_STATE_HOME/agent-browser`, defaulting to `~/.local/state/agent-browser`. `AGENT_BROWSER_STATE_DIR` selects another private directory. Use the same setting for all commands in a session.

The supervisor holds a profile lock, watches its browser and daemon, and closes the session at its deadline. Explicit stop also clears records. If the supervisor is killed, run `status` and `stop SESSION` to recover. A reboot can leave disposable data on disk. Stop stale sessions to remove it. Deleting a profile is not secure disk erasure.

Persistent profiles contain sensitive website and extension data. They stay local and outside this public skill. Output files remain until the user removes them.

Run `python3 agent-browser/tests/smoke.py` from the repository to check headless isolation, profile locks, handoff, persistence, crash recovery, and expiry against a local fixture. The test uses temporary profiles and removes them afterward.

## Sources

- [Chrome DevTools CLI](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md)
- [MCP configuration](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/configuration.md)
- [Bitwarden autofill](https://bitwarden.com/help/auto-fill-browser/)
- [Bitwarden passkeys](https://bitwarden.com/help/storing-passkeys/)
