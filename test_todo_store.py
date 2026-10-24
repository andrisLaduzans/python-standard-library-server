import tempfile
import unittest
from pathlib import Path

from database import Database
from todo import TodoField
from todo_store import TodoStore


class TodoStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Database(Path(self.temp_dir.name) / "todos.db")
        database.initialize()
        self.store = TodoStore(database)

        for idx in range(3):
            self.store.create(f"todo_{idx}")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_read(self) -> None:
        entries = self.store.read()
        self.assertEqual(3, len(entries))
        self.assertEqual(
            ["todo_0", "todo_1", "todo_2"], [entry.name for entry in entries]
        )

        with self.subTest(is_done=False):
            entries = self.store.read(is_done=False)
            self.assertEqual(3, len(entries))

        with self.subTest(is_done=True):
            for entry in entries:
                self.store.update_todo(entry.uuid, {TodoField.IS_DONE: True})
            entries = self.store.read(is_done=True)

            self.assertEqual(
                [
                    {TodoField.NAME: "todo_0", TodoField.IS_DONE: True},
                    {TodoField.NAME: "todo_1", TodoField.IS_DONE: True},
                    {TodoField.NAME: "todo_2", TodoField.IS_DONE: True},
                ],
                [
                    {TodoField.NAME: entry.name, TodoField.IS_DONE: entry.is_done}
                    for entry in entries
                ],
            )

    def test_find_by_id(self):
        non_exiting = self.store.find_by_id("non-existent")
        self.assertIsNone(non_exiting)

        with self.subTest(test="correct id"):
            all_entries = self.store.read()
            result = self.store.find_by_id(all_entries[0].uuid)

            self.assertIsNotNone(result)
            self.assertEqual(
                {TodoField.NAME: "todo_0"},
                {TodoField.NAME: result.name if result else ""},
            )
