from enum import StrEnum
from typing import TypeVar

from todo_api.error import ValidationError
from todo_api.http_layer.http_method import Method

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

    @staticmethod
    def _validate_non_empty_str(key: str, value: str | None) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"Query Param '{key}' Should Be Non-Empty String")
        return value.strip()

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
        cls, params: dict[str, list[str]], key: str, default: str | None = None
    ) -> str | None:
        value = cls._single_value(params, key)

        if value is None:
            return None if default is None else default

        value = cls._validate_non_empty_str(key, value)

        return value

    @classmethod
    def _one_of_items(cls, key: str, value: str | None, enum: type[EnumT]) -> EnumT:
        try:
            if value is None:
                raise ValueError
            return enum(value)
        except ValueError as error:
            raise ValidationError(
                f"Invalid Value For '{key}': {value}\n"
                f"Expected One Of {[item.value for item in enum]}"
            ) from error
