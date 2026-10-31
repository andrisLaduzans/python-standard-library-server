import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from todo_api.db.database import Database


class DatabaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "todos.db"

        with closing(sqlite3.connect(self.db_path)) as connection:
            with connection:
                connection.execute("""
                CREATE TABLE todos (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    is_done INTEGER NOT NULL DEFAULT 0
                        CHECK (is_done IN (0, 1))
                ) 
                """)

                connection.execute(
                    "INSERT INTO todos VALUES (?, ?, ?, ?)",
                    ("existing-id", "Existing Todo", None, 0),
                )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initialize_fails_when_existing_data_violates_constraint(self):
        with closing(sqlite3.connect(self.db_path)) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO todos VALUES (?, ?, ?, ?)",
                    ("invalid-id", "    ", None, 0),
                )

        database = Database(self.db_path)
        with self.assertRaises(sqlite3.IntegrityError):
            database.initialize()

    def test_initialize_migrates_existing_database(self):
        database = Database(self.db_path)
        database.initialize()

        with closing(database.connect()) as connection:
            row = connection.execute(
                "SELECT name FROM todos WHERE id = ?", ("existing-id",)
            ).fetchone()

            self.assertEqual(("Existing Todo",), row)

            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        INSERT INTO todos (id, name, description, is_done)
                        VALUES (?, ?, ?, ?)
                        """,
                        ("new-id", "    ", None, 0),
                    )

    def test_initialize_is_idempotent(self):
        database = Database(self.db_path)

        database.initialize()
        database.initialize()

        with closing(database.connect()) as connection:
            row = connection.execute(
                "SELECT name FROM todos WHERE id = ?", ("existing-id",)
            ).fetchone()

        self.assertEqual(("Existing Todo",), row)

    def test_empty_name_db_integrity(self):
        database = Database(self.db_path)
        database.initialize()

        with closing(database.connect()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        "INSERT INTO todos (id, name, description, is_done) VALUES (?, ?, ?, ?)",
                        ("test_id", "", None, 0),
                    )

    def test_whitespace_only_name_db_integrity(self):
        database = Database(self.db_path)
        database.initialize()

        with closing(database.connect()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        "INSERT INTO todos (id, name, description, is_done) VALUES (?, ?, ?, ?)",
                        ("test_id", "    ", None, 0),
                    )

    def test_begin_immediate_serializes_writers(self):
        with (
            closing(sqlite3.connect(self.db_path, timeout=0.1)) as connection_a,
            closing(sqlite3.connect(self.db_path, timeout=0.1)) as connection_b,
        ):
            connection_a.execute("BEGIN IMMEDIATE")

            try:
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                    connection_b.execute("BEGIN IMMEDIATE")
            finally:
                connection_a.rollback()

    def test_connect_uses_configured_timeout(self):
        database = Database(self.db_path, timeout=0.1)

        with patch(
            "todo_api.db.database.sqlite3.connect",
            wraps=sqlite3.connect,
        ) as connect:
            with closing(database.connect()):
                connect.assert_called_once_with(self.db_path, timeout=0.1)

    def test_initialize_adds_owner_id_to_existing_todos(self):
        database = Database(self.db_path)
        database.initialize()

        with closing(database.connect()) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(todos)")}
            row = connection.execute(
                "SELECT owner_id FROM todos WHERE id = ?", ("existing-id",)
            ).fetchone()

        self.assertIn("owner_id", columns)
        self.assertEqual((None,), row)
