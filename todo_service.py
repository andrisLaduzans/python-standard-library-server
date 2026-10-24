from error import TodoNotFoundError
from todo_store import TodoStore


class TodoService:
    def __init__(self, store: TodoStore):
        self._store = store

    def get_all(self, is_done: bool | None = None) -> list[dict]:
        todos = self._store.read(is_done)
        return [todo.to_dict() for todo in todos]

    def get(self, uuid: str) -> dict:
        todo = self._store.find_by_id(uuid)
        if not todo:
            raise TodoNotFoundError()
        return todo.to_dict()

    def delete(self, uuid: str) -> dict:
        deleted = self._store.delete(uuid)
        if not deleted:
            raise TodoNotFoundError()
        return deleted.to_dict()

    def create(self, name: str, description: str | None = None) -> dict:
        todo = self._store.create(name, description)
        return todo.to_dict()

    def update_todo(self, uuid: str, data: dict) -> dict:
        todo = self._store.update_todo(uuid, data)
        if not todo:
            raise TodoNotFoundError()
        return todo.to_dict()
