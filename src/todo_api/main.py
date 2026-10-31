import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from todo_api.db.database import Database
from todo_api.db.todo_store import TodoStore
from todo_api.http_layer.http_handler import HttpHandler
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.middleware import (
    AuthenticationMiddleware,
    RequestLoggingMiddleware,
)
from todo_api.http_layer.router import Router, Routes
from todo_api.http_layer.server import Server

load_dotenv()
PORT = 8000


def serve():
    logging.basicConfig(level=logging.INFO)

    server_address = ("", PORT)

    fallback_db_path = Path(__file__).resolve().parent / "todos.db"
    db_path = Path(os.getenv("TODO_DB_PATH", fallback_db_path))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    database = Database(db_path)
    database.initialize()
    store = TodoStore(database)

    router = Router()
    router.add_route(Method.GET, Routes.Todos.todos, HttpHandler.get_todos)
    router.add_route(Method.POST, Routes.Todos.todos, HttpHandler.create_todo)
    router.add_route(Method.GET, Routes.Todos.todos_id, HttpHandler.get_todo)
    router.add_route(Method.DELETE, Routes.Todos.todos_id, HttpHandler.delete_todo)
    router.add_route(Method.PATCH, Routes.Todos.todos_id, HttpHandler.update_todo)

    httpd = Server(
        server_address,
        HttpHandler,
        store,
        router,
        (RequestLoggingMiddleware, AuthenticationMiddleware),
    )

    print(f"server running at http://localhost:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
