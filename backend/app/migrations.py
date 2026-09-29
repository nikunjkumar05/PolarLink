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
}


def ensure_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)

    inspector = inspect(engine)

    with engine.begin() as conn:
        for table, columns in _COLUMNS.items():
            if table not in inspector.get_table_names():
                continue
            present = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl_type in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))
