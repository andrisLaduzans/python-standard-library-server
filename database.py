import sqlite3
from contextlib import closing
from pathlib import Path


class Database:
    def __init__(self, path: Path):
        self._path = path

    def initialize(self) -> None:
        with closing(self.connect()) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS todos(
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        is_done INTEGER NOT NULL DEFAULT 0
                            CHECK (is_done IN (0, 1))
                    ) 
                """)

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)
