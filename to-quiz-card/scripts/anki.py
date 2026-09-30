#!/usr/bin/env python3
"""Publish explicitly approved learning batches through AnkiConnect."""

import argparse
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


DECK = "Learning"
MODEL = "To Quiz Card"
FIELDS = ["CardId", "Question", "Answer", "Session", "Source"]
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
STATE = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "to-quiz-card"


class Failure(Exception):
    pass


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(path)


class Anki:
    def __init__(self):
        self.url = os.environ.get("ANKI_CONNECT_URL", "http://127.0.0.1:8765")
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise Failure("Use a localhost AnkiConnect endpoint; execute on the Anki host or use an SSH tunnel.")
        self.started = None
        self.headless = False

    def call(self, action, **params):
        data = {"action": action, "version": 6, "params": params}
        key = os.environ.get("ANKI_CONNECT_API_KEY")
        if key:
            data["key"] = key
        request = urllib.request.Request(
            self.url, json.dumps(data).encode(), {"Content-Type": "application/json"}
        )
        try:
            # Do not send a localhost API request through a configured HTTP proxy.
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=15) as response:
                result = json.load(response)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise Failure(f"AnkiConnect request {action} failed: {exc}") from exc
        if not isinstance(result, dict) or "result" not in result or "error" not in result:
            raise Failure("AnkiConnect returned an unexpected response")
        if result["error"] is not None:
            raise Failure(f"AnkiConnect {action}: {result['error']}")
        return result["result"]

    def connect(self, start=False, interactive=False):
        try:
            self.call("version")
            if interactive and self.call("toQuizCardStatus")["headless"]:
                raise Failure("An existing offscreen Anki instance must be closed before interactive studying.")
            return
        except Failure:
            if not start:
                raise
            # Only launch on connection failure, not on an authentication or API configuration error.
            try:
                self.call("version")
            except Failure as exc:
                if "Connection refused" not in str(exc):
                    raise
            else:
                raise
        executable = shutil.which("anki")
        if not executable:
            raise Failure("Anki is not on PATH")
        env = os.environ.copy()
        runtime = env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        wayland = env.get("WAYLAND_DISPLAY", "wayland-1")
        graphical = (Path(runtime) / wayland).exists()
        if graphical:
            env["XDG_RUNTIME_DIR"] = runtime
            env["WAYLAND_DISPLAY"] = wayland
        elif env.get("DISPLAY"):
            display = env["DISPLAY"].split(":")[-1].split(".")[0]
            graphical = display.isdigit() and Path(f"/tmp/.X11-unix/X{display}").exists()
        if not graphical:
            if interactive:
                raise Failure("Studying needs a graphical session; card creation can run headlessly over SSH.")
            env["QT_QPA_PLATFORM"] = "offscreen"
            env["QT_QPA_PLATFORMTHEME"] = ""
            env["QT_STYLE_OVERRIDE"] = "Fusion"
            env.pop("DISPLAY", None)
            env.pop("WAYLAND_DISPLAY", None)
            env["QTWEBENGINE_CHROMIUM_FLAGS"] = env.get("QTWEBENGINE_CHROMIUM_FLAGS", "") + " --disable-gpu"
            self.headless = True
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        log_path = STATE / "anki-startup.log"
        log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(log_fd, "a") as log:
            self.started = subprocess.Popen(
                [executable, "-p", os.environ.get("ANKI_PROFILE", "User 1")],
                env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
            )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                self.call("version")
                self.call("toQuizCardStatus")
                return
            except Failure:
                if self.started.poll() is not None:
                    break
                time.sleep(0.25)
        raise Failure(f"Anki did not expose the required API. Check {log_path}; it needs AnkiConnect and quiz-settings.")

    def close(self):
        if self.started is not None and self.headless and self.started.poll() is None:
            try:
                self.call("toQuizCardCloseHeadless")
                self.started.wait(timeout=10)
            except (Failure, subprocess.TimeoutExpired):
                # Never kill Anki with a collection open.
                print("The offscreen Anki instance remains running; close it normally before studying.", file=sys.stderr)


def ensure_model(api):
    if MODEL in api.call("modelNames"):
        if api.call("modelFieldNames", modelName=MODEL) != FIELDS:
            raise Failure("The To Quiz Card note type has incompatible fields; refusing to change it automatically.")
        templates = api.call("modelTemplates", modelName=MODEL)
        if len(templates) != 1:
            raise Failure("The To Quiz Card note type needs one template per note.")
        return
    api.call(
        "createModel", modelName=MODEL, inOrderFields=FIELDS, isCloze=False,
        css=".card {font-family: sans-serif; font-size: 22px; text-align: left;} "
            ".question, .answer {white-space: pre-wrap;} .context {font-size: 12px; opacity: .6; margin-top: 24px;}",
        cardTemplates=[{
            "Name": "Recall",
            "Front": '<div class="question">{{Question}}</div>',
            "Back": '{{FrontSide}}<hr id="answer"><div class="answer">{{Answer}}</div>'
                    '<div class="context">{{Session}}<br>{{Source}}</div>',
        }],
    )


def setup(api):
    api.call("createDeck", deck=DECK)
    preset = api.call("getDeckConfig", deck=DECK)
    if preset["name"] != "To Quiz Card":
        preset_id = api.call("cloneDeckConfigId", name="To Quiz Card", cloneFrom=str(preset["id"]))
        if not preset_id or not api.call("setDeckConfigId", decks=[DECK], configId=preset_id):
            raise Failure("Could not create the dedicated Learning preset")
        preset = api.call("getDeckConfig", deck=DECK)
    preset["desiredRetention"] = 0.9
    preset["new"]["delays"] = [10]
    preset["new"]["perDay"] = 9999
    preset["lapse"]["delays"] = [10]
    preset["rev"]["perDay"] = 9999
    if not api.call("saveDeckConfig", config=preset):
        raise Failure("Could not save the Learning preset")
    api.call("toQuizCardEnableFSRS", deck=DECK)
    ensure_model(api)
    result = api.call("toQuizCardStatus", deck=DECK)
    if not result["fsrs"]:
        raise Failure("FSRS did not enable")
    return {"deck": DECK, **result}


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise Failure(f"{label} must be nonempty text")
    return value


def validate(batch):
    if not isinstance(batch, dict):
        raise Failure("Batch must be a JSON object")
    session = text(batch.get("session_id"), "session_id")
    if not SLUG.fullmatch(session) or len(session) > 100:
        raise Failure("session_id must be a lowercase kebab-case slug, at most 100 characters")
    text(batch.get("title"), "title")
    if not isinstance(batch.get("source", ""), str):
        raise Failure("source must be text")
    concepts = batch.get("concepts")
    cards = batch.get("cards")
    if not isinstance(concepts, list) or not concepts or not isinstance(cards, list) or not cards:
        raise Failure("The batch needs approved concepts and cards")
    concept_ids = set()
    for concept in concepts:
        if not isinstance(concept, dict):
            raise Failure("Each concept must be an object")
        cid = text(concept.get("id"), "concept id")
        text(concept.get("label"), "concept label")
        if cid in concept_ids:
            raise Failure("Duplicate concept ID")
        concept_ids.add(cid)
    card_ids, questions, covered = set(), set(), set()
    for card in cards:
        if not isinstance(card, dict):
            raise Failure("Each card must be an object")
        cid = text(card.get("id"), "card id")
        if not SLUG.fullmatch(cid) or len(cid) > 100 or cid in card_ids:
            raise Failure("Card IDs must be unique lowercase kebab-case slugs, at most 100 characters")
        card_ids.add(cid)
        question = text(card.get("question"), "question")
        text(card.get("answer"), "answer")
        normalized = " ".join(question.split()).casefold()
        if normalized in questions:
            raise Failure("Duplicate question within the batch")
        questions.add(normalized)
        ids = card.get("concept_ids")
        if not isinstance(ids, list) or not ids or not all(isinstance(x, str) for x in ids) or not set(ids) <= concept_ids:
            raise Failure("Each card must reference approved concept IDs")
        covered.update(ids)
        tags = card.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) and SLUG.fullmatch(tag) for tag in tags):
            raise Failure("Tags must be lowercase kebab-case strings")
    if covered != concept_ids:
        raise Failure("Cards omit approved concepts: " + ", ".join(sorted(concept_ids - covered)))
    return batch


def card_key(session, card_id):
    return hashlib.sha256(f"{session}:{card_id}".encode()).hexdigest()


def fields(batch, card):
    return {
        "CardId": card_key(batch["session_id"], card["id"]),
        "Question": html.escape(card["question"]),
        "Answer": html.escape(card["answer"]),
        "Session": html.escape(batch["title"]),
        "Source": html.escape(batch.get("source", "")),
    }


def publish(api, batch):
    settings = api.call("toQuizCardStatus", deck=DECK)
    if not settings["fsrs"] or not settings["deck_exists"]:
        raise Failure("Run setup first to initialize Learning with FSRS")
    for group in ("new", "lapse"):
        if any(delay >= 1440 for delay in settings["preset"][group]["delays"]):
            raise Failure("The Learning preset has day-long learning steps; use short steps with FSRS")
    ensure_model(api)
    session_tag = "quiz-session-" + batch["session_id"]
    expected = {card_key(batch["session_id"], card["id"]) for card in batch["cards"]}
    existing_session = api.call("findNotes", query=f'note:"{MODEL}" tag:{session_tag}')
    if existing_session:
        existing_keys = {note["fields"]["CardId"]["value"] for note in api.call("notesInfo", notes=existing_session)}
        if existing_keys - expected:
            raise Failure("This batch omits previously published cards; preserve their IDs instead of silently deleting them")
    created, updated, unchanged, verify_ids = [], [], [], []
    for card in batch["cards"]:
        values = fields(batch, card)
        tags = sorted(set(card.get("tags", []) + ["to-quiz-card", session_tag]))
        ids = api.call("findNotes", query=f'note:"{MODEL}" CardId:{values["CardId"]}')
        if len(ids) > 1:
            raise Failure("Multiple notes have the same stable CardId")
        if ids:
            nid = ids[0]
            note = api.call("notesInfo", notes=ids)[0]
            if {name: note["fields"][name]["value"] for name in FIELDS} != values:
                api.call("updateNoteFields", note={"id": nid, "fields": values})
                updated.append(nid)
            else:
                unchanged.append(nid)
            if not set(tags) <= set(note["tags"]):
                api.call("addTags", notes=ids, tags=" ".join(tags))
        else:
            nid = api.call("addNote", note={
                "deckName": DECK, "modelName": MODEL, "fields": values,
                "tags": tags, "options": {"allowDuplicate": False},
            })
            if not isinstance(nid, int) or isinstance(nid, bool) or nid <= 0:
                raise Failure("Anki did not return a saved note ID")
            created.append(nid)
        verify_ids.append(nid)
    notes = api.call("notesInfo", notes=verify_ids)
    if len(notes) != len(batch["cards"]):
        raise Failure("Card readback was incomplete")
    by_id = {note["noteId"]: note for note in notes}
    for nid, card in zip(verify_ids, batch["cards"]):
        note = by_id.get(nid)
        if not note or not note.get("cards") or {name: note["fields"][name]["value"] for name in FIELDS} != fields(batch, card):
            raise Failure("Saved card contents failed verification")
    return {"deck": DECK, "fsrs": True, "created": len(created), "updated": len(updated),
            "unchanged": len(unchanged), "note_ids": verify_ids, "delivery": "verified"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("setup")
    commands.add_parser("study")
    commands.add_parser("remind")
    related = commands.add_parser("related")
    related.add_argument("--tag", required=True)
    upload = commands.add_parser("publish")
    upload.add_argument("batch", type=Path)
    upload.add_argument("--approved", action="store_true", help="Use only after explicit approval of this session's concept list")
    args = parser.parse_args()
    batch = None
    if args.command == "publish":
        if not args.approved:
            raise Failure("Publishing requires explicit approval; pass --approved only after the user approves the latest concept list")
        batch = validate(json.loads(args.batch.read_text(encoding="utf-8")))
    if args.command == "related" and not SLUG.fullmatch(args.tag):
        raise Failure("Use a lowercase kebab-case topic tag")
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / "operation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        batch_path = STATE / "sessions" / f"{batch['session_id']}.json" if batch else None
        if batch:
            save(batch_path, batch)
        api = Anki()
        try:
            if args.command == "remind":
                message = "Open Anki to review your learning cards."
                try:
                    api.connect()
                    due = api.call("findCards", query=f'deck:"{DECK}" is:due')
                    new = api.call("findCards", query=f'deck:"{DECK}" is:new')
                    if not due and not new:
                        emit({"notification": "skipped", "reason": "no learning cards due"})
                        return
                    message = f"{len(due)} cards due, {len(new)} new cards. Open Anki to review."
                except Failure:
                    pass
                subprocess.run(["notify-send", "Anki learning review", message], check=True)
                emit({"notification": "sent", "message": message})
                return
            api.connect(start=args.command != "status", interactive=args.command == "study")
            if args.command == "status":
                emit({"connected": True, "anki_connect_version": api.call("version"), **api.call("toQuizCardStatus", deck=DECK)})
            elif args.command == "setup":
                emit(setup(api))
            elif args.command == "study":
                if not api.call("guiDeckOverview", name=DECK):
                    raise Failure("Learning deck not found; run setup")
                emit({"deck": DECK, "opened": True})
            elif args.command == "related":
                ids = api.call("findNotes", query=f'note:"{MODEL}" tag:{args.tag}')
                emit([{"question": note["fields"]["Question"]["value"], "tags": note["tags"]}
                      for note in api.call("notesInfo", notes=ids)])
            else:
                result = publish(api, batch)
                result["batch_path"] = str(batch_path)
                save(batch_path.with_suffix(".receipt.json"), result)
                emit(result)
        except Failure as exc:
            if batch_path:
                save(batch_path.with_suffix(".receipt.json"), {"delivery": "pending", "error": str(exc)})
                print(f"Approved batch retained at {batch_path}. Retry the same batch after fixing delivery.", file=sys.stderr)
            raise
        finally:
            api.close()


if __name__ == "__main__":
    try:
        main()
    except (Failure, OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
