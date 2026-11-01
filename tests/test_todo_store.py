import sqlite3
from contextlib import closing

from tests.utils.test_store import TestStore
from todo_api.db.todo_store import TodoStore
from todo_api.todos.todo import TodoField
from todo_api.todos.todo_schemas import SortOrder, TodoSortBy


class TodoStoreTest(TestStore):
    def setUp(self) -> None:
        self._init_database("todos.db")
        self.store = TodoStore(self.database)
        self.owner_id = "user-1"

        self.store.create("todo_0", owner_id=self.owner_id)
        self.store.create("todo_1", is_done=True, owner_id=self.owner_id)
        self.store.create("todo_2", owner_id=self.owner_id)
        self.store.create("todo_3", is_done=True, owner_id=self.owner_id)

    def test_read(self) -> None:
        entries = self.store.read(owner_id=self.owner_id)
        self.assertEqual(4, len(entries))
        self.assertEqual(
            ["todo_0", "todo_1", "todo_2", "todo_3"], [entry.name for entry in entries]
        )

        with self.subTest(is_done=False):
            entries = self.store.read(is_done=False, owner_id=self.owner_id)
            self.assertEqual(2, len(entries))

        with self.subTest(is_done=True):
            entries = self.store.read(is_done=True, owner_id=self.owner_id)

            self.assertEqual(
                [
                    {TodoField.NAME: "todo_1", TodoField.IS_DONE: True},
                    {TodoField.NAME: "todo_3", TodoField.IS_DONE: True},
                ],
                [
                    {TodoField.NAME: entry.name, TodoField.IS_DONE: entry.is_done}
                    for entry in entries
                ],
            )

    def test_read_pagination(self):
        for offset in range(3):
            entries = self.store.read(limit=1, offset=offset, owner_id=self.owner_id)
            self.assertEqual(
                [{TodoField.NAME: f"todo_{offset}"}],
                [{TodoField.NAME: entry.name} for entry in entries],
            )

    def test_find_by_id(self):
        non_exiting = self.store.find_by_id("non-existent", owner_id=self.owner_id)
        self.assertIsNone(non_exiting)

        with self.subTest(test="correct id"):
            all_entries = self.store.read(owner_id=self.owner_id)
            result = self.store.find_by_id(all_entries[0].uuid, owner_id=self.owner_id)

            self.assertIsNotNone(result)
            self.assertEqual(
                {TodoField.NAME: "todo_0"},
                {TodoField.NAME: result.name if result else ""},
            )

    def test_sorting_by(self):
        entries = self.store.read(
            sort_by=TodoSortBy.NAME, sort_order=SortOrder.DESC, owner_id=self.owner_id
        )
        expected = ["todo_3", "todo_2", "todo_1", "todo_0"]
        result = [entry.name for entry in entries]
        self.assertEqual(expected, result)

    def test_search(self):
        entries = self.store.read(search=["2"], owner_id=self.owner_id)
        expected = ["todo_2"]
        result = [entry.name for entry in entries]
        self.assertEqual(expected, result)

        with self.subTest("Should join search together with is_done"):
            entries = self.store.read(search=["3"], is_done=True, owner_id=self.owner_id)
            expected = [{TodoField.NAME: "todo_3", TodoField.IS_DONE: True}]
            actual = [
                {TodoField.NAME: entry.name, TodoField.IS_DONE: entry.is_done}
                for entry in entries
            ]
            self.assertEqual(expected, actual)

        with self.subTest("Should join multiple searches with is_done"):
            entries = self.store.read(
                search=["3", "1", "2"], is_done=True, owner_id=self.owner_id
            )
            expected = [
                {TodoField.NAME: "todo_1", TodoField.IS_DONE: True},
                {TodoField.NAME: "todo_3", TodoField.IS_DONE: True},
            ]
            actual = [
                {TodoField.NAME: entry.name, TodoField.IS_DONE: entry.is_done}
                for entry in entries
            ]
            self.assertEqual(expected, actual)

    def test_update_rolls_back_when_constraint_is_violated(self):
        todo = self.store.create(
            name="Original", description="Description", owner_id=self.owner_id
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.store.update_todo(todo.uuid, {"name": "    "}, owner_id=self.owner_id)

        updated_todo = self.store.find_by_id(todo.uuid, owner_id=self.owner_id)

        self.assertIsNotNone(updated_todo)
        self.assertEqual(updated_todo.name, "Original")

    def test_create_stores_owner_id(self):
        todo = self.store.create("owned-todo", owner_id=self.owner_id)
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                "SELECT owner_id FROM todos WHERE id = ?", (todo.uuid,)
            ).fetchone()
        self.assertEqual(self.owner_id, row[0])

    def test_read_returns_only_owner_todos(self):
        owner_id = "new-owner"
        self.store.create("new-owner-todo-1", owner_id=owner_id)
        self.store.create("new-owner-todo-2", owner_id=owner_id)
        entries = self.store.read(owner_id=owner_id)
        self.assertEqual(
            ["new-owner-todo-1", "new-owner-todo-2"], [entry.name for entry in entries]
        )

    def test_find_by_id_ignores_other_owners_todos(self):
        todo = self.store.create("other-todo", owner_id="user-2")
        self.assertIsNone(self.store.find_by_id(todo.uuid, owner_id=self.owner_id))
