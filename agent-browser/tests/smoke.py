#!/usr/bin/env python3
"""Live headless checks. Requires the launcher's system dependencies."""

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

LAUNCHER = Path(__file__).resolve().parents[1] / "scripts/browser.py"


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<title>Local browser test</title><input id='field'>")

    def log_message(self, *_):
        pass


def main():
    with tempfile.TemporaryDirectory(prefix="agent-browser-smoke-") as temp:
        base = Path(temp)
        env = dict(os.environ, AGENT_BROWSER_STATE_DIR=str(base / "state"))
        server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}"

        def run(*args, ok=True):
            result = subprocess.run([sys.executable, str(LAUNCHER), *args], env=env,
                                    capture_output=True, text=True, timeout=150)
            if ok and result.returncode:
                raise AssertionError(result.stderr)
            if not ok and not result.returncode:
                raise AssertionError("Command unexpectedly succeeded: " + repr(args))
            return result.stdout

        def start(*args):
            return json.loads(run("start", "--mode", "headless", "--output-dir", str(base / "output"),
                                  "--ttl", "180", *args))["session"]

        def state(sid):
            return json.loads((base / "state/sessions" / sid / "state.json").read_text())

        def evaluate(sid, code):
            return run("tool", sid, "evaluate_script", code, "--pageId", "1")

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(start, "--profile", "test-account")
                second = pool.submit(start)
                a, b = first.result(), second.result()
            for sid in [a, b]:
                run("tool", sid, "navigate_page", "1", "--url", url)
            evaluate(a, '() => { document.cookie="agent=A; max-age=3600; path=/"; localStorage.setItem("agent", "A"); return true; }')
            assert '"cookie":""' in evaluate(b, '() => JSON.stringify({cookie:document.cookie})').replace('\\"', '"')
            assert '"A"' in evaluate(a, '() => localStorage.getItem("agent")')
            assert "null" in evaluate(b, '() => localStorage.getItem("agent")')
            run("pause", b)
            run("tool", b, "list_pages", ok=False)
            run("resume", b)
            run("tool", b, "list_pages")

            run("start", "--mode", "headless", "--profile", "test-account", ok=False)
            contenders = [json.loads(line)["session"] for line in run("status").splitlines()
                          if json.loads(line)["status"] == "failed"]
            for sid in contenders:
                run("stop", sid)
            assert '"A"' in evaluate(a, '() => localStorage.getItem("agent")')
            run("stop", a)
            c = start("--profile", "test-account")
            run("tool", c, "navigate_page", "1", "--url", url)
            assert '"A"' in evaluate(c, '() => localStorage.getItem("agent")')
            assert "agent=A" in evaluate(c, '() => document.cookie')

            os.kill(state(b)["supervisor"][0], signal.SIGKILL)
            time.sleep(0.5)
            run("stop", b)
            assert not (base / "state/sessions" / b).exists()
            run("tool", c, "list_pages")
            run("stop", c)
            assert (base / "state/profiles/test-account/browser").is_dir()

            crashed = start()
            profile = str(base / "state/sessions" / crashed / "browser").encode()
            browser_pid = None
            for entry in Path("/proc").iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    command = (entry / "cmdline").read_bytes()
                    if profile in command and b"--remote-debugging-pipe" in command and b"--type=" not in command:
                        browser_pid = int(entry.name)
                        break
                except OSError:
                    pass
            assert browser_pid, "No owned Chrome process found"
            os.kill(browser_pid, signal.SIGTERM)
            deadline = time.monotonic() + 30
            while state(crashed)["status"] not in {"closed", "failed"} and time.monotonic() < deadline:
                time.sleep(0.5)
            assert state(crashed)["status"] == "closed", state(crashed)
            run("stop", crashed)

            short = json.loads(run("start", "--mode", "headless", "--ttl", "10",
                                   "--output-dir", str(base / "output")))["session"]
            deadline = time.monotonic() + 30
            while state(short)["status"] not in {"closed", "failed"} and time.monotonic() < deadline:
                time.sleep(0.5)
            assert state(short)["status"] == "closed", state(short)
            assert not (base / "state/sessions" / short / "browser").exists()
            run("stop", short)
            print("PASS: concurrent isolation, pause/resume, profile locking, persistence, supervisor/browser exit recovery, expiry")
        finally:
            for line in run("status").splitlines():
                run("stop", json.loads(line)["session"])
            server.shutdown()


if __name__ == "__main__":
    main()
