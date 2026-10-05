"""
Database migrations.

Each migration has a unique name and a body that is either:
  - a Python callable taking a sqlite3.Connection, or
  - a SQL string (one or more statements).

Migrations are applied in list order. Their names are recorded in the
`schema_migrations` table so they never run twice.

Rules:
  - Never edit an existing migration. Add a new one.
  - Never reorder migrations.
  - If a migration is not naturally idempotent (e.g. a data migration),
    it will only run once thanks to schema_migrations.
  - Legacy migrations 001-010 are ADD COLUMN operations that must remain
    safe to run twice, so that introducing this system on an existing
    database does not error.
"""

import logging
import sqlite3

logger = logging.getLogger("researchbot")


# --- Helpers ------------------------------------------------------------


def _idempotent_add_column(conn, table, column, coltype):
    """ALTER TABLE ADD COLUMN, ignoring duplicate-column errors."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e).lower():
            raise


# --- Legacy migrations (previously inlined in database.init_db) ----------


def _m001_add_rank(conn):
    _idempotent_add_column(conn, "sources", "rank", "INTEGER DEFAULT 0")


def _m002_add_http_status(conn):
    _idempotent_add_column(conn, "sources", "http_status", "INTEGER")


def _m003_add_fetched_at(conn):
    _idempotent_add_column(conn, "sources", "fetched_at", "TIMESTAMP")


def _m004_add_parent_source_id(conn):
    _idempotent_add_column(conn, "sources", "parent_source_id", "INTEGER")


def _m005_add_source_lineage(conn):
    _idempotent_add_column(conn, "sources", "source_lineage", "TEXT")


def _m006_add_bias_score(conn):
    _idempotent_add_column(conn, "sources", "bias_score", "REAL")


def _m007_add_completeness_score(conn):
    _idempotent_add_column(conn, "sources", "completeness_score", "REAL")


def _m008_add_confidence_score(conn):
    _idempotent_add_column(conn, "claims", "confidence_score", "REAL")


def _m009_add_confidence_level(conn):
    _idempotent_add_column(conn, "claims", "confidence_level", "TEXT")


def _m010_add_confidence_explanation(conn):
    _idempotent_add_column(conn, "claims", "confidence_explanation", "TEXT")


# --- Stage 31: indexes for the queries the pipeline actually runs -------


_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_sources_research        ON sources(research_id);
CREATE INDEX IF NOT EXISTS idx_sources_canonical       ON sources(research_id, canonical_url);
CREATE INDEX IF NOT EXISTS idx_claims_research         ON claims(research_id);
CREATE INDEX IF NOT EXISTS idx_claims_source           ON claims(source_id);
CREATE INDEX IF NOT EXISTS idx_relationships_research  ON relationships(research_id);
CREATE INDEX IF NOT EXISTS idx_queries_research        ON queries(research_id);
CREATE INDEX IF NOT EXISTS idx_packages_research       ON packages(research_id);
CREATE INDEX IF NOT EXISTS idx_answers_research        ON answers(research_id);
CREATE INDEX IF NOT EXISTS idx_research_user_created   ON research(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_research_status         ON research(status);
"""


def _m011_add_indexes(conn):
    conn.executescript(_INDEXES_SQL)


# --- Registry ----------------------------------------------------------


MIGRATIONS = [
    ("001_add_rank_to_sources",                  _m001_add_rank),
    ("002_add_http_status_to_sources",           _m002_add_http_status),
    ("003_add_fetched_at_to_sources",            _m003_add_fetched_at),
    ("004_add_parent_source_id_to_sources",      _m004_add_parent_source_id),
    ("005_add_source_lineage_to_sources",        _m005_add_source_lineage),
    ("006_add_bias_score_to_sources",            _m006_add_bias_score),
    ("007_add_completeness_score_to_sources",    _m007_add_completeness_score),
    ("008_add_confidence_score_to_claims",       _m008_add_confidence_score),
    ("009_add_confidence_level_to_claims",       _m009_add_confidence_level),
    ("010_add_confidence_explanation_to_claims", _m010_add_confidence_explanation),
    ("011_add_pipeline_indexes",                 _m011_add_indexes),
]


# --- Runner ------------------------------------------------------------


def _ensure_migrations_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name       TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def _already_applied(conn, name):
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE name=?", (name,)
    ).fetchone()
    return row is not None


def _record(conn, name):
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)", (name,)
    )
    conn.commit()


def run_migrations(conn):
    """Apply any unapplied migrations. Safe to call on every startup."""
    _ensure_migrations_table(conn)

    applied_count = 0
    for name, body in MIGRATIONS:
        if _already_applied(conn, name):
            continue
        try:
            if callable(body):
                body(conn)
            else:
                conn.executescript(body)
            _record(conn, name)
            applied_count += 1
            logger.info(f"Applied migration: {name}")
        except Exception as e:
            logger.error(f"Migration '{name}' failed: {e}")
            raise
    if applied_count:
        logger.info(f"Applied {applied_count} new migration(s)")


def current_version(conn):
    """Return the name of the most recently applied migration, or None."""
    row = conn.execute(
        "SELECT name FROM schema_migrations ORDER BY name DESC LIMIT 1"
    ).fetchone()
    return row["name"] if row else None