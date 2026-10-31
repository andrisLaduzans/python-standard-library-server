from http import HTTPStatus

from tests.utils.test_server import TestServer
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
