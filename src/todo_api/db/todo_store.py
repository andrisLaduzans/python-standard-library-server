from contextlib import closing

from todo_api.db.database import Database
from todo_api.todos.todo import Todo
from todo_api.todos.todo_schemas import SortOrder, TodoListQuery, TodoSortBy


class TodoStore:
    def __init__(self, database: Database):
        self._database = database

    @staticmethod
    def _to_todo(row: tuple) -> Todo:
        todo_id, name, description, is_done = row
        return Todo(name, description, bool(is_done), todo_id)

    def create(
        self, name: str, description: str | None = None, is_done: bool = False
    ) -> Todo:
        todo = Todo(name, description, is_done)

        with closing(self._database.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO todos (id, name, description, is_done)
                    VALUES (?, ?, ?, ?) 
                    """,
                    (todo.uuid, todo.name, todo.description, int(todo.is_done)),
                )

        return todo

    def read(
        self,
        is_done: bool | None = None,
        limit: int = TodoListQuery.DEFAULT_LIMIT,
        offset: int = TodoListQuery.DEFAULT_OFFSET,
        sort_by: TodoSortBy = TodoListQuery.DEFAULT_SORT_BY,
        sort_order: SortOrder = TodoListQuery.DEFAULT_SORT_ORDER,
        search: list[str] | None = None,
    ) -> list[Todo]:
        query = "\nSELECT id, name, description, is_done\nFROM todos"

        conditions: list[str] = []
        params: list[int | str] = []

        if is_done is not None:
            conditions.append("(is_done = ?)")
            params.extend([int(is_done)])

        if search is not None and len(search):
            search_conditions: list[str] = []
            for search_str in search:
                search_conditions.append("\n(name LIKE ? OR description LIKE ?)")
                params.extend([f"%{search_str}%", f"%{search_str}%"])

            search_query = " (" + " OR ".join(search_conditions) + "\n) "
            conditions.append(search_query)

        if conditions:
            query += "\nWHERE " + " AND ".join(conditions)

        query += f"\nORDER BY {sort_by.value} {sort_order.upper()}, id ASC "

        query += "\nLIMIT ? OFFSET ? "
        params.extend((limit, offset))

        with closing(self._database.connect()) as connection:
            # debug print sql query
            # connection.set_trace_callback(print)
            rows = connection.execute(query, params).fetchall()

        return [self._to_todo(row) for row in rows]

    def find_by_id(self, todo_id: str) -> Todo | None:
        query = """
            SELECT id, name, description, is_done
            FROM todos
            WHERE id = ? 
            """
        params = (todo_id,)

        with closing(self._database.connect()) as connection:
            row = connection.execute(query, params).fetchone()

        return self._to_todo(row) if row else None

    def update_todo(self, uuid: str, args: dict) -> Todo | None:
        with closing(self._database.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")

            with connection:
                row = connection.execute(
                    """
                SELECT id, name, description, is_done
                FROM todos
                WHERE id = ? 
                """,
                    (uuid,),
                ).fetchone()

                if row is None:
                    return None

                todo = self._to_todo(row)
                todo.update(args)

                connection.execute(
                    """
                UPDATE todos
                SET name = ?, description = ?, is_done = ?
                WHERE id = ? 
                """,
                    (todo.name, todo.description, int(todo.is_done), todo.uuid),
                )

        return todo

    def delete(self, uuid: str) -> Todo | None:
        with closing(self._database.connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")

            with connection:
                row = connection.execute(
                    """
                    SELECT id, name, description, is_done
                    FROM todos
                    WHERE id = ? 
                    """,
                    (uuid,),
                ).fetchone()

                if row is None:
                    return None

                connection.execute(
                    """
                    DELETE FROM todos WHERE id = ?
                    """,
                    (uuid,),
                )
        return self._to_todo(row)
