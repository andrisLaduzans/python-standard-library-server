import sqlite3
from contextlib import closing
from pathlib import Path


class Database:
    def __init__(self, path: Path, *, timeout: float = 5.0):
        self._path = path
        self._timeout = timeout

    def initialize(self) -> None:
        with closing(self.connect()) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS todos(
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                        description TEXT,
                        is_done INTEGER NOT NULL DEFAULT 0
                            CHECK (is_done IN (0, 1))
                    ) 
                """)

                schema = connection.execute("""
                    SELECT sql
                    FROM sqlite_master
                    WHERE type = 'table' AND name = 'todos'
                """).fetchone()[0]

                if "CHECK (length(trim(name)) > 0)" not in schema:
                    connection.execute("""
                        CREATE TABLE todos_new (
                            id TEXT PRIMARY KEY,
                            name TEXT NOT NULL
                                CHECK (length(trim(name)) > 0),
                            description TEXT,
                            is_done INTEGER NOT NULL DEFAULT 0
                                CHECK (is_done IN (0, 1))
                        )
                    """)

                    connection.execute("""
                        INSERT INTO todos_new (id, name, description, is_done)
                        SELECT id, name, description, is_done
                        FROM todos
                    """)

                    connection.execute("DROP TABLE todos")
                    connection.execute("ALTER TABLE todos_new RENAME TO todos")

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=self._timeout)
