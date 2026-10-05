import sqlite3
import time

from core import database


def _use_temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file), raising=False)
    # get_connection reads DB_PATH from the module's import; patch config too
    import config
    monkeypatch.setattr(config, "DB_PATH", str(db_file))
    return db_file


def test_no_stale_jobs_returns_zero(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    database.init_db()
    assert database.recover_stale_jobs(max_age_minutes=30) == 0


def test_active_job_with_recent_update_is_not_recovered(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    database.init_db()

    user_id = database.get_or_create_user("test_user")
    rid = database.create_research(user_id, "recent job")
    database.update_research_status(rid, status="searching", stage="search")

    # Not stale — should not be recovered
    assert database.recover_stale_jobs(max_age_minutes=30) == 0

    job = database.get_research(rid)
    assert job["status"] == "searching"


def test_stale_active_job_is_recovered(tmp_path, monkeypatch):
    db_file = _use_temp_db(tmp_path, monkeypatch)
    database.init_db()

    user_id = database.get_or_create_user("test_user")
    rid = database.create_research(user_id, "old job")
    database.update_research_status(rid, status="searching", stage="search")

    # Backdate updated_at to simulate a crash 2 hours ago
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "UPDATE research SET updated_at = datetime('now', '-120 minutes') WHERE id=?",
        (rid,),
    )
    conn.commit()
    conn.close()

    recovered = database.recover_stale_jobs(max_age_minutes=30)
    assert recovered == 1

    job = database.get_research(rid)
    assert job["status"] == "failed"
    assert job["current_stage"] == "recovered"
    assert "Abandoned" in job["error"]
    assert job["completed_at"] is not None


def test_terminal_states_are_never_touched(tmp_path, monkeypatch):
    db_file = _use_temp_db(tmp_path, monkeypatch)
    database.init_db()

    user_id = database.get_or_create_user("test_user")
    rid = database.create_research(user_id, "done job")
    database.update_research_status(rid, status="completed", stage="completed")

    # Backdate
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "UPDATE research SET updated_at = datetime('now', '-1000 minutes') WHERE id=?",
        (rid,),
    )
    conn.commit()
    conn.close()

    recovered = database.recover_stale_jobs(max_age_minutes=30)
    assert recovered == 0

    job = database.get_research(rid)
    assert job["status"] == "completed"