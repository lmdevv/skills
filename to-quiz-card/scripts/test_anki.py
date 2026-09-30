"""Run with python3 -m unittest discover -s <skill>/scripts -p 'test_*.py'."""

import copy
import unittest

import anki


def batch():
    return {
        "session_id": "retry-test",
        "title": "Transactions",
        "concepts": [{"id": "c1", "label": "Atomicity"}],
        "cards": [
            {"id": "q1", "concept_ids": ["c1"], "question": "What is atomicity?",
             "answer": "All changes commit or none do.", "tags": ["databases"]},
            {"id": "q2", "concept_ids": ["c1"], "question": "Why group a transfer?",
             "answer": "Both sides must succeed together."},
        ],
    }


class MemoryAnki:
    def __init__(self):
        self.notes = {}
        self.calls = []
        self.fail_on_add = None
        self.fsrs = True

    def call(self, action, **params):
        self.calls.append(action)
        if action == "toQuizCardStatus":
            return {"fsrs": self.fsrs, "deck_exists": True,
                    "preset": {"new": {"delays": [10]}, "lapse": {"delays": [10]}}}
        if action == "modelNames":
            return [anki.MODEL]
        if action == "modelFieldNames":
            return anki.FIELDS
        if action == "modelTemplates":
            return {"Recall": {}}
        if action == "findNotes":
            query = params["query"]
            if "CardId:" in query:
                key = query.split("CardId:", 1)[1]
                return [nid for nid, note in self.notes.items()
                        if note["fields"]["CardId"]["value"] == key]
            tag = query.split("tag:", 1)[1]
            return [nid for nid, note in self.notes.items() if tag in note["tags"]]
        if action == "notesInfo":
            return [copy.deepcopy(self.notes[nid]) for nid in params["notes"]]
        if action == "addNote":
            if len(self.notes) == self.fail_on_add:
                raise anki.Failure("Simulated interrupted delivery")
            nid = len(self.notes) + 1
            note = params["note"]
            self.notes[nid] = {"noteId": nid, "cards": [nid * 10], "tags": note["tags"],
                               "fields": {k: {"value": v} for k, v in note["fields"].items()},
                               "schedule": {"due": 42, "reps": 7, "interval": 13}}
            return nid
        if action == "updateNoteFields":
            note = params["note"]
            self.notes[note["id"]]["fields"].update({k: {"value": v} for k, v in note["fields"].items()})
            return None
        if action == "addTags":
            for nid in params["notes"]:
                self.notes[nid]["tags"] += params["tags"].split()
            return None
        raise AssertionError(f"Unexpected API action: {action}")


class DeliveryTests(unittest.TestCase):
    def test_coverage_is_required(self):
        value = batch()
        value["concepts"].append({"id": "c2", "label": "Isolation"})
        with self.assertRaisesRegex(anki.Failure, "omit approved"):
            anki.validate(value)

    def test_unapproved_subject_matter_is_rejected(self):
        value = batch()
        value["cards"][0]["concept_ids"] = ["unknown"]
        with self.assertRaises(anki.Failure):
            anki.validate(value)

    def test_repeated_questions_are_rejected(self):
        value = batch()
        value["cards"][1]["question"] = "  WHAT is atomicity?  "
        with self.assertRaisesRegex(anki.Failure, "Duplicate question"):
            anki.validate(value)

    def test_retry_after_partial_delivery(self):
        api = MemoryAnki()
        api.fail_on_add = 1
        with self.assertRaises(anki.Failure):
            anki.publish(api, anki.validate(batch()))
        api.fail_on_add = None
        result = anki.publish(api, batch())
        self.assertEqual((result["created"], result["unchanged"], len(api.notes)), (1, 1, 2))
        result = anki.publish(api, batch())
        self.assertEqual((result["created"], result["unchanged"], len(api.notes)), (0, 2, 2))

    def test_correction_preserves_schedule_and_card_ids(self):
        api = MemoryAnki()
        anki.publish(api, batch())
        original = copy.deepcopy(api.notes[1])
        value = batch()
        value["cards"][0]["answer"] = "The changes are indivisible."
        result = anki.publish(api, value)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(api.notes[1]["cards"], original["cards"])
        self.assertEqual(api.notes[1]["schedule"], original["schedule"])

    def test_omission_does_not_delete_published_cards(self):
        api = MemoryAnki()
        anki.publish(api, batch())
        value = batch()
        value["cards"].pop()
        with self.assertRaisesRegex(anki.Failure, "omits previously"):
            anki.publish(api, value)
        self.assertEqual(len(api.notes), 2)

    def test_fsrs_required_before_writes(self):
        api = MemoryAnki()
        api.fsrs = False
        with self.assertRaises(anki.Failure):
            anki.publish(api, batch())
        self.assertEqual(api.notes, {})
        self.assertNotIn("addNote", api.calls)

    def test_plain_code_is_escaped_for_display(self):
        value = batch()
        value["cards"][0]["answer"] = '<script> x && y\n"quote"'
        rendered = anki.fields(value, value["cards"][0])["Answer"]
        self.assertEqual(rendered, '&lt;script&gt; x &amp;&amp; y\n&quot;quote&quot;')


if __name__ == "__main__":
    unittest.main()
