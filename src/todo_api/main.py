import logging
from functools import partial

from todo_api.config import load_db_path
from todo_api.db.database import Database
from todo_api.db.todo_store import TodoStore
from todo_api.db.token_store import TokenStore
from todo_api.http_layer.http_handler import HttpHandler
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.middleware import (
    AuthenticationMiddleware,
    RequestLoggingMiddleware,
)
from todo_api.http_layer.router import Router, Routes
from todo_api.http_layer.server import Server
from todo_api.todos.todo_service import TodoService
from todo_api.todos.views import TodoViews

PORT = 8000


def serve():
    logging.basicConfig(level=logging.INFO)

    server_address = ("", PORT)

    database = Database(load_db_path())
    database.initialize()

    store = TodoStore(database)
    token_store = TokenStore(database)
    views = TodoViews(TodoService(store))

    router = Router()
    router.add_route(Method.GET, Routes.Todos.todos, views.list_todos)
    router.add_route(Method.POST, Routes.Todos.todos, views.create_todo)
    router.add_route(Method.GET, Routes.Todos.todos_id, views.get_todo)
    router.add_route(Method.DELETE, Routes.Todos.todos_id, views.delete_todo)
    router.add_route(Method.PATCH, Routes.Todos.todos_id, views.update_todo)

    httpd = Server(
        server_address,
        HttpHandler,
        store,
        router,
        middlewares=(
            RequestLoggingMiddleware,
            partial(AuthenticationMiddleware, token_store=token_store),
        ),
    )

    print(f"server running at http://localhost:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
