from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

from error import ValidationError
from http_method import Method
from todo import Todo, TodoField

EnumT = TypeVar("EnumT", bound=StrEnum)


class SchemaValidator:
    @staticmethod
    def _required_string(data: dict, key: str) -> str:
        value = data.get(key)

        if key not in data:
            raise ValidationError(f"Field '{key}' Is Required")

        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"'{key}' Must Be A Non-Empty String")

        return value.strip()

    @staticmethod
    def _validate_data(method: Method, data: dict):
        if not isinstance(data, dict):
            raise ValidationError("Expected JSON object")

        if len(data.items()) == 0:
            raise ValidationError(f"{method} Body Must Not Be Empty")

    @staticmethod
    def _validate_writable_fields(fields: list, data: dict):
        for field in data:
            if field not in fields:
                raise ValidationError(f"Unknown Field '{field}'")

    @staticmethod
    def _single_value(params: dict[str, list[str]], key: str) -> str | None:
        values = params.get(key)

        if values is None:
            return None

        if len(values) != 1:
            raise ValidationError(f"More Than One Query Param With Key: '{key}'")

        return values[0]

    @classmethod
    def _parse_bool(cls, params: dict[str, list[str]], key) -> bool | None:
        value = cls._single_value(params, key)

        if value is None:
            return None

        if value not in ("true", "false"):
            raise ValidationError(f"'{key}' Must Be 'true' or 'false'")

        return value == "true"

    @classmethod
    def _parse_int(cls, params: dict[str, list[str]], key, default) -> int:
        value = cls._single_value(params, key)
        if value is None:
            return default

        try:
            value = int(value)
            if value < 0:
                raise ValidationError(f"Query Param '{key}' must be positive number")

            return value
        except ValueError as error:
            raise ValidationError(f"Query Param '{key}' Must Be An Integer") from error

    @classmethod
    def _parse_str(
        cls, params: dict[str, list[str]], key: str, default: str | None
    ) -> str | None:
        value = cls._single_value(params, key)

        if value is None:
            return None if default is None else default

        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"Query Param '{key}' Should Be Non-Empty String")

        return value

    @classmethod
    def _one_of_items(cls, key: str, value: str | None, enum: type[EnumT]) -> EnumT:
        try:
            if value is None:
                raise ValueError
            return enum(value)
        except ValueError:
            raise ValidationError(
                f"Invalid Value For '{key}': {value}\n"
                f"Expected One Of {[item.value for item in enum]}"
            )


class TodoSortBy(StrEnum):
    ID = "rowid"
    NAME = TodoField.NAME
    DESCRIPTION = TodoField.DESCRIPTION
    IS_DONE = TodoField.IS_DONE


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class TodoListQuery(SchemaValidator):
    is_done: bool | None = None
    limit: int = 20
    offset: int = 0
    sort_by: TodoSortBy = TodoSortBy.ID
    sort_order: SortOrder = SortOrder.ASC

    MAX_LIMIT = 100
    ALLOWED_SORT_BY = [TodoSortBy.NAME, TodoSortBy.DESCRIPTION, TodoSortBy.IS_DONE]

    @classmethod
    def from_query_params(
        cls, params: dict[str, list[str]] | None = None
    ) -> TodoListQuery:
        params = params or {}

        is_done = SchemaValidator._parse_bool(params, "is_done")
        limit = SchemaValidator._parse_int(params, "limit", default=20)
        offset = SchemaValidator._parse_int(params, "offset", default=0)
        sort_by = SchemaValidator._parse_str(params, "sort_by", default=TodoSortBy.ID)
        sort_order = SchemaValidator._parse_str(
            params, "sort_order", default=SortOrder.ASC
        )

        if not 1 <= limit <= cls.MAX_LIMIT:
            raise ValidationError(f"'limit' Must Be Between 1 And {cls.MAX_LIMIT}")

        if offset < 0:
            raise ValidationError("'offset' Must Be Non-Negative")

        sort_by = SchemaValidator._one_of_items("sort_by", sort_by, TodoSortBy)
        sort_order = SchemaValidator._one_of_items("sort_order", sort_order, SortOrder)

        return cls(
            is_done=is_done,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def __str__(self) -> str:
        return str(self.to_dict())

    def to_dict(self) -> dict[str, bool | None | int | str]:
        return {
            TodoField.IS_DONE.value: self.is_done,
            "limit": self.limit,
            "offset": self.offset,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
        }


class TodoCreateRequest(SchemaValidator):
    def __init__(self, name: str, description: str | None = None):
        self.name = name
        self.description = description

    @classmethod
    def from_dict(cls, data: dict) -> TodoCreateRequest:
        super()._validate_data(Method.POST, data)
        super()._validate_writable_fields(Todo.CREATE_FIELDS, data)

        name = super()._required_string(data, TodoField.NAME)

        description = data.get(TodoField.DESCRIPTION)
        if description is not None:
            description = super()._required_string(data, TodoField.DESCRIPTION)

        return cls(name, description)


class TodoUpdateRequest(SchemaValidator):
    @classmethod
    def from_dict(cls, data: dict) -> dict:
        super()._validate_data(Method.PATCH, data)

        if TodoField.ID in data:
            raise ValidationError("ID Field Cannot Be Modified")

        super()._validate_writable_fields(Todo.UPDATE_FIELDS, data)

        updated = {}
        for key, value in data.items():
            if key == TodoField.DESCRIPTION:
                if value is None:
                    updated[key] = None
                    continue

                if not isinstance(value, str):
                    raise ValidationError(f"Invalid Type For '{key}'")

                value = value.strip()
                if not value:
                    raise ValidationError(f"'{key}' Must Be A Non-Empty String")

                updated[key] = value
                continue

            expected_type = Todo.WRITABLE_FIELDS[key]

            if type(value) is not expected_type:
                raise ValidationError(f"Invalid Type For '{key}'")

            if isinstance(value, str):
                value = value.strip()
                if not value:
                    raise ValidationError(f"'{key}' Must Not Be A Non-Empty String")

            updated[key] = value

        return updated
