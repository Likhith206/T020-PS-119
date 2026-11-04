"""
TENDERLENS — Database Engine
Provides clean SQLite connection pooling, schema initialization, and transactional context.
Strictly enables foreign keys and parameterized SQL.
"""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional


class Database:
    def __init__(self, db_path: str = "database/tenderlens.db", schema_path: str = "database/schema.sql"):
        self.db_path = db_path
        self.schema_path = schema_path
        self._mem_conn = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:")
            self._mem_conn.row_factory = sqlite3.Row
            self._mem_conn.execute("PRAGMA foreign_keys = ON;")
        elif self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a connection with foreign keys and Row factory enabled."""
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self, drop_existing: bool = False) -> None:
        """Initializes tables, indexes, and triggers from schema.sql."""
        schema_file = Path(self.schema_path)
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found at {self.schema_path}")

        if drop_existing and self.db_path != ":memory:" and Path(self.db_path).exists():
            Path(self.db_path).unlink()

        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        conn = self.get_connection()
        conn.executescript(schema_sql)
        conn.commit()
        if self._mem_conn is None:
            conn.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Transactional context manager with automatic commit/rollback."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if self._mem_conn is None:
                conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Executes a SELECT query and returns rows as dictionaries."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            if self._mem_conn is None:
                conn.close()

    def execute_scalar(self, query: str, params: tuple = ()) -> Optional[any]:
        """Executes a scalar query and returns the single value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row[0] if row else None
