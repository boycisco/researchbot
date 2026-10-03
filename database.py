import sqlite3
import json
from datetime import datetime
from config import DB_PATH
import models

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript(models.SCHEMA)
        conn.commit()

        # Read the current columns after schema creation
        existing_columns = [row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()]

        migrations = [
            ("rank",               "ALTER TABLE sources ADD COLUMN rank INTEGER DEFAULT 0"),
            ("http_status",        "ALTER TABLE sources ADD COLUMN http_status INTEGER"),
            ("fetched_at",         "ALTER TABLE sources ADD COLUMN fetched_at TIMESTAMP"),
            ("parent_source_id",   "ALTER TABLE sources ADD COLUMN parent_source_id INTEGER"),
            ("source_lineage",     "ALTER TABLE sources ADD COLUMN source_lineage TEXT"),
            ("bias_score",         "ALTER TABLE sources ADD COLUMN bias_score REAL"),
            ("completeness_score", "ALTER TABLE sources ADD COLUMN completeness_score REAL"),
        ]

        for column_name, sql in migrations:
            if column_name not in existing_columns:
                conn.execute(sql)
                conn.commit()

# User helpers
def get_or_create_user(telegram_id):
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
        if not user:
            cur = conn.execute("INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,))
            conn.commit()
            user_id = cur.lastrowid
            return user_id
        return user['id']

# Research helpers
def create_research(user_id, topic):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO research (user_id, topic, status, current_stage) VALUES (?,?,?,?)",
            (user_id, topic, 'received', 'received')
        )
        conn.commit()
        return cur.lastrowid

def update_research_status(research_id, status=None, stage=None, error=None, intent=None):
    with get_connection() as conn:
        fields = []
        params = []
        if status is not None:
            fields.append("status=?")
            params.append(status)
        if stage is not None:
            fields.append("current_stage=?")
            params.append(stage)
        if error is not None:
            fields.append("error=?")
            params.append(error)
        if intent is not None:
            fields.append("intent=?")
            params.append(intent)
        fields.append("updated_at=CURRENT_TIMESTAMP")
        query = f"UPDATE research SET {', '.join(fields)} WHERE id=?"
        params.append(research_id)
        conn.execute(query, params)
        conn.commit()

def set_cancel_requested(research_id, cancel=True):
    with get_connection() as conn:
        conn.execute("UPDATE research SET cancel_requested=? WHERE id=?", (1 if cancel else 0, research_id))
        conn.commit()

def is_cancel_requested(research_id):
    with get_connection() as conn:
        row = conn.execute("SELECT cancel_requested FROM research WHERE id=?", (research_id,)).fetchone()
        return bool(row['cancel_requested']) if row else False

def get_research(research_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM research WHERE id=?", (research_id,)).fetchone()

def get_user_research(user_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM research WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()

# Query helpers
def insert_queries(research_id, queries):
    with get_connection() as conn:
        for q in queries:
            conn.execute(
                "INSERT INTO queries (research_id, query, purpose, priority) VALUES (?,?,?,?)",
                (research_id, q['query'], q.get('purpose',''), q.get('priority',1))
            )
        conn.commit()

def get_queries(research_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM queries WHERE research_id=?", (research_id,)).fetchall()

# Source helpers
def insert_source(research_id, query_id, source):
    canonical = source.get('canonical_url') or source.get('url')
    with get_connection() as conn:
        # Deduplicate by canonical_url within the same research
        existing = conn.execute(
            "SELECT id FROM sources WHERE research_id=? AND canonical_url=?",
            (research_id, canonical)
        ).fetchone()
        if existing:
            return existing['id']

        cur = conn.execute("""
            INSERT INTO sources 
            (research_id, query_id, url, canonical_url, title, domain, snippet, rank)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            research_id, query_id, source.get('url'), canonical,
            source.get('title'), source.get('domain'), source.get('snippet'),
            source.get('rank', 0)
        ))
        conn.commit()
        return cur.lastrowid

def update_source_fetch(source_id, fetch_data):
    with get_connection() as conn:
        conn.execute("""
            UPDATE sources SET
                content=?, word_count=?, title=?, published_at=?,
                fetch_status=?, http_status=?, fetched_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (
            fetch_data.get('content'),
            fetch_data.get('word_count'),
            fetch_data.get('title'),
            fetch_data.get('published_at'),
            fetch_data.get('status'),
            fetch_data.get('http_status'),
            source_id
        ))
        conn.commit()

def update_source_verification(source_id, verify_data):
    with get_connection() as conn:
        conn.execute("""
            UPDATE sources SET
                relevance_score=?, quality_score=?, evidence_score=?,
                recency_score=?, bias_score=?, completeness_score=?,
                source_type=?, is_primary=?,
                verification_status=?
            WHERE id=?
        """, (
            verify_data.get('relevance_score'),
            verify_data.get('quality_score'),
            verify_data.get('evidence_score'),
            verify_data.get('recency_score'),
            verify_data.get('bias_score'),
            verify_data.get('completeness_score'),
            verify_data.get('source_type'),
            1 if verify_data.get('is_primary') else 0,
            verify_data.get('status'),
            source_id
        ))
        conn.commit()

def get_sources_for_research(research_id, only_verified=False):
    query = "SELECT * FROM sources WHERE research_id=?"
    if only_verified:
        query += " AND verification_status='verified'"
    with get_connection() as conn:
        return conn.execute(query, (research_id,)).fetchall()

# Claim helpers
def insert_claim(research_id, source_id, claim_data):
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO claims (research_id, source_id, claim, claim_type, evidence, support_level, confidence)
            VALUES (?,?,?,?,?,?,?)
        """, (
            research_id, source_id, claim_data['claim'], claim_data.get('claim_type'),
            claim_data.get('evidence'), claim_data.get('support_level'),
            claim_data.get('confidence', 0.0)
        ))
        conn.commit()
        return cur.lastrowid

def get_claims(research_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM claims WHERE research_id=?", (research_id,)).fetchall()

# Relationship helpers
def insert_relationship(research_id, claim_a, claim_b, rel_data):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO relationships (research_id, claim_a, claim_b, relationship, reason, confidence)
            VALUES (?,?,?,?,?,?)
        """, (
            research_id, claim_a, claim_b, rel_data['relationship'],
            rel_data.get('reason'), rel_data.get('confidence', 0.0)
        ))
        conn.commit()

def get_relationships(research_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM relationships WHERE research_id=?", (research_id,)).fetchall()

# Package helpers
def store_package(research_id, content):
    with get_connection() as conn:
        conn.execute("INSERT INTO packages (research_id, content) VALUES (?,?)", (research_id, content))
        conn.commit()

def get_latest_package(research_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM packages WHERE research_id=? ORDER BY created_at DESC LIMIT 1", (research_id,)).fetchone()

# Answer helpers
def store_answer(research_id, content, verification_status):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO answers (research_id, content, verification_status) VALUES (?,?,?)",
            (research_id, content, verification_status)
        )
        conn.commit()

def get_answer(research_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM answers WHERE research_id=? ORDER BY created_at DESC LIMIT 1", (research_id,)).fetchone()

# User state helpers
def set_user_state(telegram_id, state, pending_topic=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO user_states (telegram_id, state, pending_topic)
            VALUES (?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET state=excluded.state, pending_topic=excluded.pending_topic, updated_at=CURRENT_TIMESTAMP
        """, (telegram_id, state, pending_topic))
        conn.commit()

def get_user_state(telegram_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM user_states WHERE telegram_id=?", (telegram_id,)).fetchone()
        if row:
            return {'state': row['state'], 'pending_topic': row['pending_topic']}
        return None

def clear_user_state(telegram_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM user_states WHERE telegram_id=?", (telegram_id,))
        conn.commit()