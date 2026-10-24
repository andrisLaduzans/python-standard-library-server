import os
from pathlib import Path

from dotenv import load_dotenv

from database import Database
from http_handler import HttpHandler
from router import Router
from server import Server
from todo_store import TodoStore

load_dotenv()
PORT = 8000


def serve():
    server_address = ("", PORT)

    fallback_db_path = Path(__file__).resolve().parent / "todos.db"
    db_path = Path(os.getenv("TODO_DB_PATH", fallback_db_path))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    database = Database(db_path)
    database.initialize()
    store = TodoStore(database)

    router = Router()
    router.add_route("GET", "/todos", HttpHandler.get_todos)
    router.add_route("POST", "/todos", HttpHandler.create_todo)
    router.add_route("GET", "/todos/:id", HttpHandler.get_todo)
    router.add_route("DELETE", "/todos/:id", HttpHandler.delete_todo)
    router.add_route("PATCH", "/todos/:id", HttpHandler.update_todo)

    httpd = Server(server_address, HttpHandler, store, router)

    print(f"server running at http://localhost:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
