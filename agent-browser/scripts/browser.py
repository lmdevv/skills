#!/usr/bin/env python3
"""Separate Chrome DevTools sessions for Linux, with optional Hyprland windows."""

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

VERSION = "1.10.1"
SCRIPT = Path(__file__).resolve()


def root():
    base = os.environ.get("AGENT_BROWSER_STATE_DIR")
    if not base:
        base = str(Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "agent-browser")
    path = Path(base).expanduser().absolute()
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or path.stat().st_uid != os.getuid():
        raise RuntimeError("State directory must be owned by you and not be a symlink")
    path.chmod(0o700)
    return path


def session_path(sid):
    if not re.fullmatch(r"[a-f0-9]{32}", sid):
        raise RuntimeError("Invalid session ID")
    return root() / "sessions" / sid


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


@contextlib.contextmanager
def locked(path, nonblocking=False):
    with path.open("a") as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
        except BlockingIOError:
            raise RuntimeError("Profile is already in use by another agent") from None
        yield


def proc_token(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (OSError, IndexError):
        return None


def alive(identity):
    return bool(identity and identity[1] and proc_token(identity[0]) == identity[1])


def matching_browsers(profile):
    # Chromium can rewrite /proc/cmdline as one space-separated process title.
    flag = re.compile(rb"(?:^|[\x00 ])" + re.escape(f"--user-data-dir={profile}".encode()) + rb"(?=[\x00 ]|$)")
    result = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            executable = (entry / "exe").resolve().name.lower()
            if (entry.stat().st_uid == os.getuid()
                    and any(name in executable for name in ["chrome", "chromium"])
                    and flag.search((entry / "cmdline").read_bytes())):
                result.append([int(entry.name), proc_token(entry.name)])
        except OSError:
            pass
    return result


def terminate(identities, group=False):
    for sig, seconds in [(signal.SIGTERM, 8), (signal.SIGKILL, 2)]:
        for identity in identities:
            if alive(identity):
                with contextlib.suppress(ProcessLookupError):
                    if group and os.getpgid(identity[0]) == identity[0]:
                        os.killpg(identity[0], sig)
                    else:
                        os.kill(identity[0], sig)
        deadline = time.monotonic() + seconds
        while any(alive(identity) for identity in identities) and time.monotonic() < deadline:
            time.sleep(0.1)
    if any(alive(identity) for identity in identities):
        raise RuntimeError("Owned browser did not exit; profile retained")


def env_for(config):
    env = dict(os.environ)
    env["CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS"] = "1"
    if config["runtime"]:
        env["XDG_RUNTIME_DIR"] = config["runtime"]
    else:
        env.pop("XDG_RUNTIME_DIR", None)
    return env


def cli(config, args, capture=True, timeout=90):
    command = config["cli"] + ["--sessionId=" + config["id"]] + args
    result = subprocess.run(command, env=env_for(config), text=True,
                            capture_output=capture, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "DevTools command failed").strip())
    return result.stdout or ""


def daemon_dir(config):
    name = "chrome-devtools-mcp-" + config["id"]
    return Path(config["runtime"]) / name if config["runtime"] else Path("/tmp") / f"{name}-{os.getuid()}"


def daemon_identity(config):
    pid = int((daemon_dir(config) / "daemon.pid").read_text())
    token = proc_token(pid)
    marker = ("CHROME_DEVTOOLS_MCP_SESSION_ID=" + config["id"]).encode()
    if not token or marker not in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0"):
        raise RuntimeError("Daemon PID does not belong to this session")
    return [pid, token]


def hypr(code):
    result = subprocess.run(["hyprctl", "eval", code], capture_output=True, text=True, timeout=5)
    if result.returncode or result.stdout.strip() != "ok":
        raise RuntimeError("Hyprland Lua rule failed: " + result.stdout + result.stderr)


def rule(config, enabled):
    name = "agent-browser-" + config["id"]
    if enabled:
        hypr('hl.window_rule({name="' + name + '", match={class="^' + name
             + '$"}, workspace="special:' + config["workspace"]
             + ' silent", no_initial_focus=true, suppress_event="activate activatefocus"})')
    else:
        hypr('hl.window_rule({name="' + name + '", enabled=false})')


def cleanup(config, state):
    if "daemon" not in state:
        with contextlib.suppress(OSError, ValueError, RuntimeError):
            state["daemon"] = daemon_identity(config)
    # Never invoke the upstream CLI against a recycled daemon PID.
    if alive(state.get("daemon")):
        try:
            cli(config, ["stop"], timeout=20)
        except (RuntimeError, subprocess.TimeoutExpired):
            terminate([state["daemon"]], group=True)
    terminate(matching_browsers(config["profile_path"]))
    if config["mode"] == "desktop":
        try:
            rule(config, False)
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            print(str(error), file=sys.stderr)
    if not config["persistent"] and Path(config["profile_path"]).exists():
        shutil.rmtree(config["profile_path"], ignore_errors=False)
    shutil.rmtree(daemon_dir(config), ignore_errors=True)
    if not config["runtime"]:
        socket = Path("/tmp") / f'chrome-devtools-mcp-{config["id"]}-{os.getuid()}.sock'
        socket.unlink(missing_ok=True)


def serve(sid):
    folder = session_path(sid)
    config = read(folder / "config.json")
    state = {"status": "starting", "supervisor": [os.getpid(), proc_token(os.getpid())]}
    write(folder / "state.json", state)
    stop = False

    def request_stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    guard = Path(config["profile_path"]).parent / ".profile.lock"
    try:
        with locked(guard, nonblocking=True):
            if matching_browsers(config["profile_path"]):
                raise RuntimeError("Profile still has a browser. Stop its owning session first")
            Path(config["profile_path"]).mkdir(mode=0o700, exist_ok=True)
            state["owns_profile"] = True
            write(folder / "state.json", state)
            try:
                if config["mode"] == "desktop":
                    rule(config, True)
                args = ["start", "--executablePath=" + config["browser"],
                        "--userDataDir=" + config["profile_path"],
                        "--headless=" + str(config["mode"] == "headless").lower(),
                        "--no-usage-statistics", "--no-performance-crux",
                        "--redactNetworkHeaders", "--categoryExtensions=true",
                        "--workspace=" + config["output_dir"]]
                if config["mode"] == "desktop":
                    args += ["--chromeArg=--ozone-platform=wayland",
                             "--chromeArg=--class=agent-browser-" + sid]
                for extension in config["extensions"]:
                    args.append("--workspace=" + extension)
                cli(config, args)
                state["daemon"] = daemon_identity(config)
                write(folder / "state.json", state)
                cli(config, ["list_pages"])
                for extension in config["extensions"]:
                    cli(config, ["install_extension", extension])
                state["status"] = "running"
                write(folder / "state.json", state)
                deadline = time.monotonic() + config["ttl"]
                while not stop and time.monotonic() < deadline:
                    if not alive(state["daemon"]) or not matching_browsers(config["profile_path"]):
                        break
                    time.sleep(0.5)
            finally:
                state["status"] = "stopping"
                write(folder / "state.json", state)
                with locked(folder / "commands.lock"):
                    cleanup(config, state)
        state["status"] = "closed"
    except Exception as error:
        state.update(status="failed", error=str(error))
    write(folder / "state.json", state)


def start(args):
    browser = shutil.which(args.browser) if args.browser else (shutil.which("chromium") or shutil.which("google-chrome"))
    if not browser:
        raise RuntimeError("Install Chromium or Chrome, or pass --browser /path/to/browser")
    if not shutil.which("npx") or not shutil.which("node"):
        raise RuntimeError("Node.js and npx are required for the pinned Chrome DevTools CLI")
    if args.mode == "desktop" and not (os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("Desktop mode needs the Hyprland session environment. Use --mode headless over SSH")
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.workspace):
        raise RuntimeError("Workspace name may contain letters, digits, underscores, and hyphens")
    if args.profile and not re.fullmatch(r"[a-zA-Z0-9_-]+", args.profile):
        raise RuntimeError("Use a profile name, not a path to an existing personal profile")
    extensions = [str(Path(path).expanduser().resolve()) for path in args.extension]
    for extension in extensions:
        if not (Path(extension) / "manifest.json").is_file():
            raise RuntimeError("Extension must be an unpacked directory with manifest.json: " + extension)
    sid = uuid.uuid4().hex
    folder = session_path(sid)
    folder.mkdir(mode=0o700, parents=True)
    profile_parent = root() / "profiles" / args.profile if args.profile else folder
    profile_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if profile_parent.is_symlink() or (profile_parent / "browser").is_symlink():
        raise RuntimeError("Agent profiles must not be symlinks to other browser data")
    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = {"id": sid, "mode": args.mode, "workspace": args.workspace,
              "browser": browser, "profile_path": str(profile_parent / "browser"),
              "persistent": args.profile, "extensions": extensions,
              "output_dir": str(output), "runtime": os.environ.get("XDG_RUNTIME_DIR"),
              "ttl": args.ttl, "cli": [shutil.which("npx"), "--yes", "--package=chrome-devtools-mcp@" + VERSION, "chrome-devtools"]}
    write(folder / "config.json", config)
    with (folder / "launcher.log").open("w") as log:
        process = subprocess.Popen([sys.executable, str(SCRIPT), "_serve", sid],
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if (folder / "state.json").exists():
            state = read(folder / "state.json")
            if state["status"] == "running":
                print(json.dumps({"session": sid, "mode": args.mode, "profile": args.profile,
                                  "workspace": "special:" + args.workspace if args.mode == "desktop" else None,
                                  "expires_in_seconds": args.ttl, "output_dir": str(output)}))
                return
            if state["status"] == "failed":
                raise RuntimeError(state["error"] + f". Session: {sid}")
        if process.poll() is not None:
            raise RuntimeError(f"Launcher exited. Inspect {folder / 'launcher.log'}")
        time.sleep(0.2)
    process.terminate()
    raise RuntimeError(f"Startup timed out. Session {sid}; use stop to finish cleanup")


def get(sid):
    folder = session_path(sid)
    return folder, read(folder / "config.json"), read(folder / "state.json")


def stop_session(sid):
    folder, config, state = get(sid)
    if alive(state.get("supervisor")):
        os.kill(state["supervisor"][0], signal.SIGTERM)
        deadline = time.monotonic() + 45
        while alive(state["supervisor"]) and time.monotonic() < deadline:
            time.sleep(0.2)
        if alive(state["supervisor"]):
            raise RuntimeError("Cleanup is still running. Retry stop after the current tool call finishes")
    else:
        # Recover a killed supervisor without touching another session's profile.
        if state.get("owns_profile") and state["status"] != "closed":
            with locked(Path(config["profile_path"]).parent / ".profile.lock", nonblocking=True):
                with locked(folder / "commands.lock"):
                    cleanup(config, state)
    final = read(folder / "state.json")
    if final["status"] != "closed" and final.get("owns_profile") and matching_browsers(config["profile_path"]):
        raise RuntimeError("Browser still running; session records retained")
    if final.get("error"):
        print(final["error"], file=sys.stderr)
    shutil.rmtree(folder)
    print("Stopped " + sid)


def tool(args):
    folder, config, _ = get(args.session)
    if not args.arguments:
        raise RuntimeError("Supply a Chrome DevTools tool, for example list_pages")
    if args.arguments[0] in {"start", "stop", "status"} or any("session" in a.lower() and a.startswith("--") for a in args.arguments):
        raise RuntimeError("Use this launcher's lifecycle commands; session overrides are not allowed")
    with locked(folder / "commands.lock"):
        state = read(folder / "state.json")
        if (folder / "paused").exists():
            raise RuntimeError("Session paused for human control. Resume only after the user hands it back")
        if (state["status"] != "running" or not alive(state.get("daemon"))
                or not alive(state.get("supervisor")) or not matching_browsers(config["profile_path"])):
            raise RuntimeError("Session is not running. Stop it and start a new session")
        cli(config, args.arguments, capture=False)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    launch = sub.add_parser("start")
    launch.add_argument("--mode", choices=["desktop", "headless"], required=True)
    launch.add_argument("--profile", help="Explicit persistent profile name")
    launch.add_argument("--workspace", default="magic", help="Hyprland special workspace name")
    launch.add_argument("--browser", help="System Chrome or Chromium executable")
    launch.add_argument("--extension", action="append", default=[], help="Unpacked extension directory, repeatable")
    launch.add_argument("--output-dir", default=str(Path.cwd()), help="Directory allowed for DevTools file tools")
    launch.add_argument("--ttl", type=int, default=14400, help="Maximum session lifetime in seconds, default 4 hours")
    for name in ["stop", "pause", "resume", "_serve"]:
        sub.add_parser(name).add_argument("session")
    sub.add_parser("status")
    call = sub.add_parser("tool")
    call.add_argument("session")
    call.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == "start":
        if args.ttl < 10:
            parser.error("--ttl must be at least 10 seconds")
        start(args)
    elif args.command == "_serve":
        serve(args.session)
    elif args.command == "stop":
        stop_session(args.session)
    elif args.command == "tool":
        tool(args)
    elif args.command == "status":
        for file in sorted((root() / "sessions").glob("*/state.json")):
            state = read(file)
            config = read(file.parent / "config.json")
            print(json.dumps({"session": config["id"], "mode": config["mode"],
                              "profile": config["persistent"], "status": state["status"],
                              "supervisor_alive": alive(state.get("supervisor")),
                              "paused": (file.parent / "paused").exists()}))
    else:
        folder, _, _ = get(args.session)
        with locked(folder / "commands.lock"):
            state = read(folder / "state.json")
            if state["status"] != "running" or not alive(state.get("supervisor")):
                raise RuntimeError("Session is not running")
            if args.command == "pause":
                (folder / "paused").touch()
            else:
                (folder / "paused").unlink(missing_ok=True)
        print(args.command + " " + args.session)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
