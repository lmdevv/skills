---
name: machine-context
description: Use when a task may need another machine, the Tailscale tailnet, or choosing how to preview a dev server in T3 Code vs reaching a service across machines
disable-model-invocation: true
user-invocable: true
metadata:
  opencode/autoinvoke: false
---

# Machine context

The user's machines share a Tailscale network with MagicDNS:

- `nixos`: The main and most powerful computer. It runs NixOS and doubles as the homelab server.
- `dawin`: An M4 MacBook Air and the user's main interface to everything.
- `iphone-14-pro`: The user's main phone, running iOS. It is not assumed to provide shell access.

Determine which machine you are on before making machine-specific decisions. Use Tailscale names to reach the others.

You have permission to connect to either computer, run commands, move files, and hop between them as needed. Choose the machine best suited to the task. Prefer `nixos` for heavy work, services, and long-running jobs. Do not wait for separate permission unless the requested task itself requires confirmation.

## Scratch work

If you are developing, building, or adding extra files and the work is not already in a repo the user named, do not dump it in a home directory or a random folder on `nixos` or `dawin`. Create a new directory under `/tmp` on the machine you are using, put everything there, and give the user the full path. Leave it in `/tmp` unless they ask to move it somewhere specific.

## T3 Code preview vs Tailscale

In T3 Code, prefer live `mcp__t3_code__preview_*` tools when a task needs a browser preview and they appear in the live tool registry. Do not assume they are missing from a short static listing.

1. Call `mcp__t3_code__preview_status` first.
2. If no usable preview tab exists, call `mcp__t3_code__preview_open`.
3. Start the dev server with the repository's documented command. Keep it running and read its actual listening port. Do not assume a fixed port.
4. Navigate with `environment-port`:

```js
await tools.mcp__t3_code__preview_navigate({
  target: {
    kind: "environment-port",
    port: ACTUAL_PORT,
    protocol: "http"
  }
});
```

5. Call `mcp__t3_code__preview_snapshot` before interacting. Prefer snapshot locators for click and type.

`environment-port` reaches a port in the active coding environment. It does not need Tailscale, a `.ts.net` hostname, public port forwarding, or Vite `allowedHosts` changes. Do not add Tailscale just to preview a local dev server in T3 Code.

Use Tailscale when another physical machine or tailnet device must reach a service directly. A `.ts.net` hostname is Tailscale. A path like `/api/assets` is only an app or proxy route.

Follow repository-specific preview instructions when present. Some projects need their own remote-control or sharing URL instead of T3 Preview.

At the end you should just give a URL link to open the dev server or file or project remotely.
