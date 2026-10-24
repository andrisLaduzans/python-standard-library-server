from http.server import HTTPServer

from router import Router
from todo_store import TodoStore


class Server(HTTPServer):
    def __init__(
        self, server_address, request_handler_class, store: TodoStore, router: Router
    ):
        self.store = store
        self.router = router
        super().__init__(server_address, request_handler_class)
