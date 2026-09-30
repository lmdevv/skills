# Anki delivery

## Setup

The helper needs Python 3 on Linux or macOS, desktop Anki, AnkiConnect, and the
bundled scheduling add-on. Automatic desktop detection and headless startup
target Linux. On macOS, open Anki first.

1. Install [AnkiConnect](https://git.sr.ht/~foosoft/anki-connect) using its
   installation instructions.
2. In Anki, open Tools > Add-ons > View Files. If it opens a specific add-on, go
   up to `addons21`. Copy [assets/quiz-settings](../assets/quiz-settings) into
   that directory as `toquizcard`.
3. Restart Anki, then run `python3 <skill-directory>/scripts/anki.py setup`.

Anki loads the copied `toquizcard/__init__.py`. See the official
[add-on folder instructions](https://addon-docs.ankiweb.net/addon-folders.html).
For Nix-managed Anki, declare both add-ons in the Nix configuration instead of
copying into immutable directories. Package the bundled Python file with
`anki-utils.buildAnkiAddon`.

The scheduling add-on adds narrow API actions to inspect and enable global FSRS.
It uses Anki's internal backend and was tested with Anki 26.08. If a different
version rejects these actions, stop and report the incompatibility.

The endpoint defaults to `http://127.0.0.1:8765`. Keep it bound to localhost.
Execute on the Anki host or forward the port through SSH. Set `ANKI_CONNECT_URL`
for a different localhost port and `ANKI_CONNECT_API_KEY` if the add-on requires
a key. Never save the key in session artifacts. `ANKI_PROFILE` selects a profile
when starting Anki, defaulting to `User 1`.

## Commands

```sh
python3 <skill-directory>/scripts/anki.py status
python3 <skill-directory>/scripts/anki.py setup
python3 <skill-directory>/scripts/anki.py related --tag databases
python3 <skill-directory>/scripts/anki.py publish <batch.json> --approved
python3 <skill-directory>/scripts/anki.py study
python3 <skill-directory>/scripts/anki.py remind
```

`status` checks without starting Anki. `setup`, `related`, `publish`, and
`study` can start it. `study` needs a desktop. The helper closes only offscreen
instances it started itself. Run `setup` once, or when the user asks to restore
its defaults.

`remind` uses `notify-send` on Linux and needs a desktop notification service.
It sends a reminder without opening Anki. Configure a daily user timer
separately if wanted. The skill includes no timer and makes no changes to
notification schedules.

## Approved batch

Save batches under `$XDG_DATA_HOME/to-quiz-card/sessions`, defaulting to
`~/.local/share/to-quiz-card/sessions`. Keep private session content outside
this skill repository. Use a unique lowercase session slug, often a date, topic,
and random suffix. Preserve card IDs across retries. Every approved concept must
appear in at least one card.

```json
{
  "session_id": "2026-09-30-transactions-a41e",
  "title": "Database transactions",
  "source": "Current learning conversation",
  "concepts": [
    {"id": "c1", "label": "Atomicity"},
    {"id": "c2", "label": "Transaction boundaries"}
  ],
  "cards": [
    {
      "id": "q1",
      "concept_ids": ["c1"],
      "question": "What does atomicity guarantee in a database transaction?",
      "answer": "The transaction's changes commit together or none take effect.",
      "tags": ["databases", "transactions"]
    },
    {
      "id": "q2",
      "concept_ids": ["c2"],
      "question": "Why put both sides of a balance transfer in one transaction?",
      "answer": "The debit and credit must succeed together; partial success corrupts the transfer.",
      "tags": ["databases", "transactions"]
    }
  ]
}
```

`source` and `tags` are optional. Tags use lowercase kebab-case. Questions and
answers are plain text; the helper escapes them for Anki's HTML display.

The helper uses the Learning deck, a To Quiz Card note type, and stable
first-field identifiers. Corrections update existing notes without resetting
scheduling. It refuses batches that omit previously published cards from the
same session. Deletion needs a separate user request.

Failed deliveries retain the approved batch and a pending receipt. Retry it with
the earlier approval instead of regenerating identifiers. Report success only
after verified readback.

## Scheduling

Setup seeds 90% desired retention, 10-minute learning and relearning steps, and
daily limits of 9999 so imports are not truncated. Existing reviews keep their
dates. FSRS schedules cards as the user reviews them. The user reveals the
answer and grades recall with Again, Hard, Good, or Easy. Forgotten answers get
Again.

Sources: [FSRS settings](https://docs.ankiweb.net/deck-options.html#fsrs),
[Anki reviewing](https://docs.ankiweb.net/studying.html).

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s <skill-directory>/scripts -p 'test_*.py'
```

These tests use an in-memory API fixture and never write cards to a real Anki
profile.
