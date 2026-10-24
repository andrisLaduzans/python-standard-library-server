from contextlib import closing

from database import Database
from todo import Todo


class TodoStore:
    def __init__(self, database: Database):
        self._database = database

    @staticmethod
    def _to_todo(row: tuple) -> Todo:
        todo_id, name, description, is_done = row
        return Todo(name, description, bool(is_done), todo_id)

    def create(self, name: str, description: str | None = None) -> Todo:
        todo = Todo(name, description)

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

    def read(self, is_done: bool | None = None) -> list[Todo]:
        query = """
            SELECT id, name, description, is_done
            FROM todos 
            """

        params = ()

        if is_done is not None:
            query += " WHERE is_done = ?"
            params = (int(is_done),)

        query += " ORDER BY rowid"

        with closing(self._database.connect()) as connection:
            rows = connection.execute(query, params).fetchall()

        return [self._to_todo(row) for row in rows]

    def find_by_id(self, todo_id: str) -> Todo | None:
        with closing(self._database.connect()) as connection:
            row = connection.execute(
                """
            SELECT id, name, description, is_done
            FROM todos
            WHERE id = ? 
            """,
                (todo_id,),
            ).fetchone()

        return self._to_todo(row) if row else None

    def update_todo(self, uuid: str, args: dict) -> Todo | None:
        with closing(self._database.connect()) as connection:
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
