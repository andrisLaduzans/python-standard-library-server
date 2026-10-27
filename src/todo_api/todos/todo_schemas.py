from dataclasses import dataclass
from enum import StrEnum

from todo_api.error import ValidationError
from todo_api.http_layer.http_method import Method
from todo_api.schema_validator import SchemaValidator
from todo_api.todos.todo import Todo, TodoField


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
    MAX_LIMIT = 100
    ALLOWED_SORT_BY = [TodoSortBy.NAME, TodoSortBy.DESCRIPTION, TodoSortBy.IS_DONE]
    MAX_SEARCH_LIMIT = 224
    DEFAULT_LIMIT = 20
    DEFAULT_OFFSET = 0
    DEFAULT_SORT_BY = TodoSortBy.ID
    DEFAULT_SORT_ORDER = SortOrder.ASC

    is_done: bool | None = None
    limit: int = DEFAULT_LIMIT
    offset: int = DEFAULT_OFFSET
    sort_by: TodoSortBy = DEFAULT_SORT_BY
    sort_order: SortOrder = DEFAULT_SORT_ORDER
    search: list[str] | None = None

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

        search = params.get("search")
        if search is not None:
            search = [
                search_str
                for search_str in search
                if SchemaValidator._parse_str({"search_str": [search_str]}, "search_str")
                is not None
            ]

            for it in search:
                if len(it) > cls.MAX_SEARCH_LIMIT:
                    raise ValidationError(
                        f"'search' Over Max Length Of {cls.MAX_SEARCH_LIMIT} Characters"
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
            search=search,
        )

    def __str__(self) -> str:
        return str(self.to_dict())

    def to_dict(self) -> dict[str, bool | None | int | str | list[str]]:
        return {
            TodoField.IS_DONE.value: self.is_done,
            "limit": self.limit,
            "offset": self.offset,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "search": self.search,
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
