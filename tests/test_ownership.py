from http import HTTPStatus

from tests.utils.test_server import TestServer
from todo_api.error import TodoNotFoundError
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.router import Routes
from todo_api.todos.todo import TodoField


class TestOwnership(TestServer):
    def test_list_excludes_other_users_todos(self):
        self.store.create("other-todo", owner_id="other-user")
        response, data = self.request(Method.GET, Routes.Todos.todos)
        self.assertEqual(HTTPStatus.OK, response.status)
        self.assertEqual(5, len(data))
        self.assertNotIn("other-todo", [item[TodoField.NAME] for item in data])

    def test_other_users_todo_returns_404(self):
        other = self.store.create("other-todo", owner_id="other-user")
        path = Routes.Todos.with_id(other.uuid)

        for method, body in (
            (Method.GET, None),
            (Method.PATCH, {TodoField.NAME: "hijacked"}),
            (Method.DELETE, None),
        ):
            with self.subTest(method=method):
                response, data = self.request(method, path, body)

                self.assert_error(
                    response,
                    data,
                    HTTPStatus.NOT_FOUND,
                    TodoNotFoundError.ERROR.code,
                    TodoNotFoundError.ERROR.message,
                )

        unchanged = self.store.find_by_id(other.uuid, owner_id="other-user")
        assert unchanged is not None
        self.assertEqual("other-todo", unchanged.name)
