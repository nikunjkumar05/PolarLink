from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from .db import Base

# SQLite cannot add columns through create_all. This keeps the prototype's
# schema in step with the models without pulling in Alembic yet.
_COLUMNS = {
    "asset_versions": {
        "passage_count": "INTEGER NOT NULL DEFAULT 0",
        "processing_note": "TEXT",
    },
    "evidence_passages": {
        "embedding": "BLOB",
        "embedding_model": "TEXT",
    },
}

# FR-11 keyword index. Content is duplicated here on purpose so keyword search
# can filter on asset/version without a join; it is rebuilt by services/index.py.
_EXTRA_SQL = [
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS passage_fts USING fts5(
        passage_id UNINDEXED,
        asset_id UNINDEXED,
        asset_version_id UNINDEXED,
        content,
        tokenize='porter unicode61'
    )
    """,
]


def ensure_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, columns in _COLUMNS.items():
            if table not in tables:
                continue
            present = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl_type in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))

            tables = set(inspector.get_table_names())

        for statement in _EXTRA_SQL:
            conn.execute(text(statement))

        for statement in _REPAIR_SQL:
            conn.execute(text(statement))


# Repairs rows orphaned by asset deletion (SQLite ran without foreign_keys=ON)
# and rebuilds the keyword index whenever it disagrees with the passages table.
_REPAIR_SQL = [
    """
    DELETE FROM evidence_passages
    WHERE asset_id NOT IN (SELECT id FROM assets)
       OR asset_version_id NOT IN (SELECT id FROM asset_versions)
    """,
    """
    INSERT INTO passage_fts (passage_id, asset_id, asset_version_id, content)
    SELECT p.id, p.asset_id, p.asset_version_id, p.content
    FROM evidence_passages p
    WHERE p.id NOT IN (SELECT CAST(passage_id AS INTEGER) FROM passage_fts)
    """,
    """
    DELETE FROM passage_fts
    WHERE CAST(passage_id AS INTEGER) NOT IN (SELECT id FROM evidence_passages)
    """,
]
