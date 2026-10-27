import unittest
from urllib.parse import parse_qs

from todo_api.error import ValidationError
from todo_api.todos.todo import TodoField
from todo_api.todos.todo_schemas import SortOrder, TodoListQuery, TodoSortBy


class TodoListQueryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.default_parsed_qs = {
            "is_done": None,
            "limit": 20,
            "offset": 0,
            "sort_by": TodoSortBy.ID,
            "sort_order": SortOrder.ASC,
            "search": None,
        }

    def test_query_params(self):
        with self.subTest("Should parse empty query"):
            parsed = parse_qs("")
            result = TodoListQuery.from_query_params(parsed)

            self.assertEqual(self.default_parsed_qs, result.to_dict())

        with self.subTest("Should throw if multiple same values"):
            parsed_qs = parse_qs("is_done=true&is_done=false")
            with self.assertRaises(ValidationError) as ctx:
                TodoListQuery.from_query_params(parsed_qs)

            self.assertEqual(
                "More Than One Query Param With Key: 'is_done'",
                ctx.exception.message,
            )

        with self.subTest("Should ignore unknown query params"):
            parsed_qs = parse_qs("campaign=google&message=lala&message=again")
            result = TodoListQuery.from_query_params(parsed_qs)
            self.assertEqual(self.default_parsed_qs, result.to_dict())

    def test_query_params_boolean_value(self):
        with self.subTest("Should throw if string"):
            parsed = parse_qs("is_done=asdf")
            with self.assertRaises(ValidationError) as ctx:
                TodoListQuery.from_query_params(parsed)
            self.assertIn(
                f"'{TodoField.IS_DONE}' Must Be 'true' or 'false'", ctx.exception.message
            )

        with self.subTest("Should parse valid boolean"):
            parsed_qs = parse_qs("is_done=true")
            result = TodoListQuery.from_query_params(parsed_qs)
            self.assertEqual(
                {**self.default_parsed_qs, "is_done": True}, result.to_dict()
            )

    def test_throw_pagination_not_numbers(self):
        with self.subTest("Should throw if pagination not numbers"):
            for key in ["limit", "offset"]:
                parsed_qs = parse_qs(f"{key}=abc")
                with self.assertRaises(ValidationError) as ctx:
                    TodoListQuery.from_query_params(parsed_qs)

                self.assertEqual(
                    f"Query Param '{key}' Must Be An Integer", ctx.exception.message
                )

    def test_throw_pagination_negative_numbers(self):
        with self.subTest("Should throw if pagination negative numbers"):
            for key in ["limit", "offset"]:
                parsed_qs = parse_qs(f"{key}=-1")
                with self.assertRaises(ValidationError) as ctx:
                    TodoListQuery.from_query_params(parsed_qs)
                self.assertIn(
                    f"Query Param '{key}' must be positive number", ctx.exception.message
                )

        with self.subTest("Should parse valid pagination params"):
            parsed_qs = parse_qs("limit=10&offset=20")
            result = TodoListQuery.from_query_params(parsed_qs)
            self.assertEqual(
                {**self.default_parsed_qs, "limit": 10, "offset": 20}, result.to_dict()
            )

    def test_query_params_pagination_out_of_bounds(self):
        with self.subTest("Should throw if page size out of bounds"):
            for limit in [0, TodoListQuery.MAX_LIMIT + 1]:
                parsed_qs = parse_qs(f"limit={limit}&offset=0")
                with self.assertRaises(ValidationError) as ctx:
                    TodoListQuery.from_query_params(parsed_qs)

                self.assertIn(
                    f"'limit' Must Be Between 1 And {TodoListQuery.MAX_LIMIT}",
                    ctx.exception.message,
                )

    def test_query_params_sort_by(self):
        with self.subTest("Should throw if invalid sort_by value"):
            parsed_qs = parse_qs("sort_by=invalid_field")
            with self.assertRaises(ValidationError) as ctx:
                TodoListQuery.from_query_params(parsed_qs)

            self.assertEqual(
                (
                    f"Invalid Value For 'sort_by': invalid_field\n"
                    f"Expected One Of {[item.value for item in TodoSortBy]}"
                ),
                ctx.exception.message,
            )

    def test_query_params_search(self):
        with self.subTest("Should throw if search param present with empty value"):
            parsed_qs = parse_qs("search=  &something_else=else")
            with self.assertRaises(ValidationError):
                TodoListQuery.from_query_params(parsed_qs)

        with self.subTest("Should join if multiple search params present"):
            parsed_qs = parse_qs("search=I like&search=coca cola")
            result = TodoListQuery.from_query_params(parsed_qs)
            self.assertEqual(
                {**self.default_parsed_qs, "search": ["I like", "coca cola"]},
                result.to_dict(),
            )

        with self.subTest("Should throw if search longer than 224 chars"):
            parsed_qs = parse_qs(f"search={'x' * (TodoListQuery.MAX_SEARCH_LIMIT + 1)}")
            with self.assertRaises(ValidationError):
                TodoListQuery.from_query_params(parsed_qs)

        with self.subTest("Should not parse 0 as falsy value"):
            parsed_qs = parse_qs("search=0")
            result = TodoListQuery.from_query_params(parsed_qs)
            self.assertEqual(
                {**self.default_parsed_qs, "search": ["0"]}, result.to_dict()
            )
