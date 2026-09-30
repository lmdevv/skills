"""Expose verified FSRS settings through AnkiConnect, without a general eval endpoint."""

import sys

import aqt
from aqt.qt import QGuiApplication, QTimer


def status(self, deck="Learning"):
    col = self.collection()
    item = col.decks.by_name(deck)
    settings = col._backend.get_deck_configs_for_update(item["id"] if item else 1)
    return {
        "fsrs": settings.fsrs,
        "deck_exists": item is not None,
        "headless": QGuiApplication.platformName() == "offscreen",
        "preset": self.getDeckConfig(deck) if item else None,
    }


def enable_fsrs(self, deck="Learning"):
    col = self.collection()
    self.createDeck(deck)
    settings = col._backend.get_deck_configs_for_update(col.decks.by_name(deck)["id"])
    col._backend.update_deck_configs(
        target_deck_id=col.decks.by_name(deck)["id"],
        configs=[item.config for item in settings.all_config],
        removed_config_ids=[],
        mode=0,
        card_state_customizer=settings.card_state_customizer,
        limits=settings.current_deck.limits,
        new_cards_ignore_review_limit=settings.new_cards_ignore_review_limit,
        fsrs=True,
        apply_all_parent_limits=settings.apply_all_parent_limits,
        fsrs_reschedule=False,
        fsrs_health_check=False,
    )
    self.window().reset()
    return status(self, deck)


def close_headless(self):
    if QGuiApplication.platformName() != "offscreen":
        raise Exception("Refusing to close an interactive Anki window")
    QTimer.singleShot(200, self.window().close)
    return True


def register():
    for module in list(sys.modules.values()):
        cls = getattr(module, "AnkiConnect", None)
        if isinstance(cls, type) and hasattr(cls, "handler"):
            for name, method in (
                ("toQuizCardStatus", status),
                ("toQuizCardEnableFSRS", enable_fsrs),
                ("toQuizCardCloseHeadless", close_headless),
            ):
                method.api = True
                method.versions = ()
                setattr(cls, name, method)
            return


aqt.gui_hooks.profile_did_open.append(register)
