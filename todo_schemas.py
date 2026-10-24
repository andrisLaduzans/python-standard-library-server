from error import ValidationError
from todo import Todo, TodoField


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
    def _validate_data(method: str, data: dict):
        if not isinstance(data, dict):
            raise ValidationError("Expected JSON object")

        if len(data.items()) == 0:
            raise ValidationError(f"{method} Body Must Not Be Empty")

    @staticmethod
    def _validate_writable_fields(fields: list, data: dict):
        for field in data:
            if field not in fields:
                raise ValidationError(f"Unknown Field '{field}'")


class TodoListQuery(SchemaValidator):
    def __init__(self, is_done: bool | None = None):
        self.is_done = is_done

    @classmethod
    def from_query_params(
        cls, params: dict[str, list[str]] | None = None
    ) -> TodoListQuery:
        if not params:
            return cls()

        values = params.get(TodoField.IS_DONE)
        if values is None:
            return cls()

        if len(values) != 1 or values[0] not in ("true", "false"):
            raise ValidationError(f"'{TodoField.IS_DONE}' Must Be 'true' or 'false'")

        return cls(is_done=values[0] == "true")

    def __str__(self) -> str:
        return str({TodoField.IS_DONE.value: self.is_done})


class TodoCreateRequest(SchemaValidator):
    def __init__(self, name: str, description: str | None = None):
        self.name = name
        self.description = description

    @classmethod
    def from_dict(cls, data: dict) -> TodoCreateRequest:
        super()._validate_data("POST", data)
        super()._validate_writable_fields(Todo.CREATE_FIELDS, data)

        name = super()._required_string(data, TodoField.NAME)

        description = data.get(TodoField.DESCRIPTION)
        if description is not None:
            description = super()._required_string(data, TodoField.DESCRIPTION)

        return cls(name, description)


class TodoUpdateRequest(SchemaValidator):
    @classmethod
    def from_dict(cls, data: dict) -> dict:
        super()._validate_data("PATCH", data)

        if TodoField.ID in data:
            raise ValidationError("ID Field Cannot Be Modified")

        super()._validate_writable_fields(Todo.UPDATE_FIELDS, data)

        updated = {}
        for key, value in data.items():
            expected_type = Todo.WRITABLE_FIELDS[key]

            if value is None and key == TodoField.DESCRIPTION:
                updated[key] = None
                continue

            if type(value) is not expected_type:
                raise ValidationError(f"Invalid Type For '{key}'")

            if isinstance(value, str):
                value = value.strip()
                if not value:
                    raise ValidationError(f"'{key}' Must Not Be A Non-Empty String")

            updated[key] = value

        return updated
