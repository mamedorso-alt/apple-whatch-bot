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


def test_link_moves_telegram_from_stale_user():
    """Reinstall app → new User; same Telegram must link via fresh code without 'another account' error."""
    db = FakeSession()
    old_user = make_user(language="ru", telegram_user_id=888)
    new_user = make_user(language="ru", telegram_user_id=None)
    new_user.is_linked = False
    db.users.extend([old_user, new_user])
    db.link_codes.append(make_link_code(new_user.id, "NEWCODE"))

    reply = link_telegram(db, telegram_user_id=888, raw_code="NEWCODE")

    assert "успешно" in reply.lower()
    assert old_user.telegram_user_id is None
    assert old_user.is_linked is False
    assert new_user.telegram_user_id == 888
    assert new_user.is_linked is True


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


def test_help_contains_sales_commands():
    db = FakeSession()
    user = make_user(language="ru", telegram_user_id=777)
    db.users.append(user)
    reply = build_command_reply(db, telegram_user_id=777, text="/help")
    assert "/weekly" in reply
    assert "/plan" in reply
    assert "/ask" in reply
    assert "/weight" in reply


def test_weight_command_records():
    db = FakeSession()
    user = make_user(language="ru", telegram_user_id=777)
    db.users.append(user)
    reply = build_command_reply(db, telegram_user_id=777, text="/weight 72.4")
    assert "сохран" in reply.lower() or "saved" in reply.lower()
    assert len(db.user_profiles) == 1
    assert len(db.user_body_metrics) == 1
