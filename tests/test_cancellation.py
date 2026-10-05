import sqlite3

from core import database


def _use_temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file), raising=False)
    import config
    monkeypatch.setattr(config, "DB_PATH", str(db_file))
    return db_file


def test_cancel_flag_defaults_to_false(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    database.init_db()

    user_id = database.get_or_create_user("u")
    rid = database.create_research(user_id, "topic")

    assert database.is_cancel_requested(rid) is False


def test_set_cancel_requested_sets_flag(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    database.init_db()

    user_id = database.get_or_create_user("u")
    rid = database.create_research(user_id, "topic")

    database.set_cancel_requested(rid, True)
    assert database.is_cancel_requested(rid) is True


def test_set_cancel_requested_can_be_reset(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    database.init_db()

    user_id = database.get_or_create_user("u")
    rid = database.create_research(user_id, "topic")

    database.set_cancel_requested(rid, True)
    database.set_cancel_requested(rid, False)
    assert database.is_cancel_requested(rid) is False


def test_is_cancel_requested_unknown_id_returns_false(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    database.init_db()
    assert database.is_cancel_requested(999999) is False


def test_cancellation_persists_across_connections(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    database.init_db()

    user_id = database.get_or_create_user("u")
    rid = database.create_research(user_id, "topic")

    # Set in one "session"
    database.set_cancel_requested(rid, True)

    # Read in another
    assert database.is_cancel_requested(rid) is True