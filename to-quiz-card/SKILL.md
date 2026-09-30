---
name: to-quiz-card
description: Review a learning conversation, then publish approved flashcards to desktop Anki.
disable-model-invocation: true
user-invocable: true
metadata:
  opencode/autoinvoke: false
---

# To quiz card

Turn this conversation's learning into Anki cards. Include questions asked
during development. Use available context. Ask for a transcript if needed,
rather than inventing missing history.

## Review first

Present a compact, numbered list with stable concept IDs such as `c1`. Include
definitions, mechanisms, comparisons, architectural tradeoffs, misconceptions,
repeated questions, and examples that helped. Label inferred pain points.
Separate discussed material from demonstrated understanding and unresolved
questions.

Invite corrections and wait for explicit approval of the latest list, such as
"LGTM", "approved", or "no more changes". Revisions replace the previous
proposal. Silence, invoking this skill, and approving the Anki setup do not
approve session content.

## Make the cards

After approval, cover every approved concept. Aim for roughly 20 questions when
useful, fewer for short sessions, or more for complete coverage. Five useful
cards is a target, not a minimum. Prefer one recall target per card. Mix
definitions, explanations, comparisons, and small scenarios. Preserve
assumptions behind architectural choices. Avoid code trivia, repetitive
questions, unapproved subjects, and answers to unresolved questions.

Keep answers concise enough for honest self-grading. Use plain text and code
where useful. Check existing questions with the helper's `related --tag <topic>`
command when topic tags are known.

## Deliver to Anki

Read [delivery and setup](references/delivery.md). Resolve the skill directory
from this file's path and run its `scripts/anki.py` helper with Python 3 on the
Anki host, or through a localhost SSH tunnel. Without shell access to a
connected host, report the missing connection.

Save approved batches outside the project under the helper's session directory.
Keep session and card IDs stable across retries and corrections. Run
`publish <batch.json> --approved`. The helper checks coverage, creates or
updates notes, verifies saved contents, and preserves review schedules. Use
AnkiConnect rather than editing Anki's database.

Leave scheduling to FSRS. New cards stay new until reviewed. Never fabricate
reviews or assign fixed 1/3/7/14-day dates. Run `setup` once if needed. It
enables global FSRS and seeds a dedicated Learning preset at 90% desired
retention without rescheduling existing reviews. Preserve later user changes.

Report created, updated, and unchanged counts, the deck, and the saved batch
path. On failure, report pending delivery and retry the same approved batch
after fixing the connection. A saved batch alone is not a successful delivery.
An AnkiWeb account is optional for desktop-only use.
