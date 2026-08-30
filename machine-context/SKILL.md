---
name: machine-context
description: Use when a task may benefit from the user's other machines or Tailscale network
---

# Machine context

The user's machines share a Tailscale network with MagicDNS:

- `nixos`: The main and most powerful computer. It runs NixOS and doubles as the homelab server.
- `dawin`: An M4 MacBook Air and the user's main interface to everything.
- `iphone-14-pro`: The user's main phone, running iOS. It is not assumed to provide shell access.

Determine which machine you are on before making machine-specific decisions. Use Tailscale names to reach the others.

You have permission to connect to either computer, run commands, move files, and hop between them as needed. Choose the machine best suited to the task. Prefer `nixos` for heavy work, services, and long-running jobs. Do not wait for separate permission unless the requested task itself requires confirmation.
