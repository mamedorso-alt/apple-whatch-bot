from app.services.telegram import build_command_reply, link_telegram
from tests.conftest import FakeSession, make_link_code, make_user


def test_link_flow_success():
    db = FakeSession()
    user = make_user(language="ru", telegram_user_id=None)
    db.users.append(user)
    db.link_codes.append(make_link_code(user.id, "ABC123"))

    reply = link_telegram(db, telegram_user_id=777, raw_code="ABC123")

    assert "успешно" in reply.lower()
    assert user.telegram_user_id == 777
    assert user.is_linked is True
    assert db.link_codes[0].used_at is not None


def test_lang_command_switch():
    db = FakeSession()
    user = make_user(language="ru", telegram_user_id=777)
    db.users.append(user)

    reply = build_command_reply(db, telegram_user_id=777, text="/lang en")

    assert "english" in reply.lower()
    assert user.language == "en"


def test_unknown_command():
    db = FakeSession()
    reply = build_command_reply(db, telegram_user_id=777, text="/something")
    assert "неизвест" in reply.lower()


def test_help_contains_coach_command():
    db = FakeSession()
    reply = build_command_reply(db, telegram_user_id=777, text="/help")
    assert "/coach" in reply
