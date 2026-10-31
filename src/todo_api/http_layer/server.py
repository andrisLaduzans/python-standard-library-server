from http.server import HTTPServer

from todo_api.db.todo_store import TodoStore
from todo_api.http_layer.middleware import Middleware
from todo_api.http_layer.router import Router


class Server(HTTPServer):
    def __init__(
        self,
        server_address,
        request_handler_class,
        store: TodoStore,
        router: Router,
        middlewares: tuple[type[Middleware], ...],
    ):
        self.store = store
        self.router = router
        self.middlewares = middlewares
        super().__init__(server_address, request_handler_class)
