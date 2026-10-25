import uuid
from enum import StrEnum
from typing import Literal


class TodoField(StrEnum):
    ID = "id"
    NAME = "name"
    DESCRIPTION = "description"
    IS_DONE = "is_done"


class Todo:
    WRITABLE_FIELDS = {
        TodoField.NAME: str,
        TodoField.DESCRIPTION: str | None,
        TodoField.IS_DONE: bool,
    }
    CREATE_FIELDS = frozenset({TodoField.NAME, TodoField.DESCRIPTION})
    UPDATE_FIELDS = frozenset(WRITABLE_FIELDS)

    def __init__(
        self,
        name: str,
        description: str | None = None,
        is_done: bool = False,
        todo_id: str | None = None,
    ):
        self.__uuid = todo_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.is_done = is_done

    @property
    def uuid(self) -> str:
        return self.__uuid

    def to_dict(self) -> dict[str, str | None | bool]:
        return {
            TodoField.ID: self.__uuid,
            TodoField.NAME: self.name,
            TodoField.DESCRIPTION: self.description,
            TodoField.IS_DONE: self.is_done,
        }

    def update(self, args: dict) -> Todo:
        for name, value in args.items():
            if name not in self.UPDATE_FIELDS:
                raise ValueError(f"Cannot update field: {name}")
            setattr(self, name, value)
        return self

    def __str__(self) -> str:
        return (
            "{\n"
            f"\t{TodoField.ID}: {self.__uuid}\n"
            f"\t{TodoField.NAME}: {self.name}\n"
            f"\t{TodoField.DESCRIPTION}: {self.description}\n"
            f"\t{TodoField.IS_DONE}: {str(self.is_done)}\n"
            "}"
        )

    def __repr__(self) -> str:
        return (
            "{\n"
            f"\t'uuid': {self.__uuid},\n"
            f"\t'{TodoField.NAME}': {self.name},\n"
            f"\t'{TodoField.DESCRIPTION}': {self.description},\n"
            f"\t'{TodoField.IS_DONE}': {self.is_done}\n"
            "}"
        )
