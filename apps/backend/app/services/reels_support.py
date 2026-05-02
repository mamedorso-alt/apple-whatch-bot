from __future__ import annotations

from app.core.config import get_settings

REELS_BUTTON_RU = "🎬 Сценарий рилса"
REELS_BUTTON_EN = "🎬 Reel script"
REELS_TRIGGER_TEXTS = frozenset({REELS_BUTTON_RU, REELS_BUTTON_EN})


def parse_reels_telegram_user_ids(raw: str) -> list[int]:
    out: list[int] = []
    for part in (raw or "").split(","):
        p = part.strip()
        if p.isdigit():
            out.append(int(p))
    return out


def reels_allowlisted_ids() -> set[int]:
    return set(parse_reels_telegram_user_ids(get_settings().reels_agent_telegram_user_ids))


def is_reels_allowlisted(telegram_user_id: int) -> bool:
    if not get_settings().reels_agent_enabled:
        return False
    return telegram_user_id in reels_allowlisted_ids()


def reels_reply_keyboard_markup(lang: str) -> dict:
    label = REELS_BUTTON_EN if lang == "en" else REELS_BUTTON_RU
    return {
        "keyboard": [[{"text": label}]],
        "resize_keyboard": True,
    }
