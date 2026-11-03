from collections.abc import Callable
from enum import StrEnum

from todo_api.error import MethodNotAllowedError, NotFoundError
from todo_api.http_layer.http_method import Method
from todo_api.http_layer.http_request import HttpRequest
from todo_api.http_layer.http_response import HttpResponse

type View = Callable[[HttpRequest, dict[str, str]], HttpResponse]


class Routes:
    class Todos(StrEnum):
        todos = "/todos"
        todos_id = f"{todos}/:id"

        @classmethod
        def with_id(cls, todo_id: str) -> str:
            return cls.todos_id.replace(":id", todo_id)


class Route:
    def __init__(self, method: Method, path_str: Routes.Todos, action: View):
        self.method = method
        self.path_str = path_str
        self.action = action

    def __str__(self) -> str:
        return self.path_str

    def to_dict(self) -> dict:
        return {"method": self.method, "path": self.path_str}


class Router:
    def __init__(self):
        self.__routes: list[Route] = []

    def add_route(self, method: Method, path_str: Routes.Todos, view: View) -> None:
        self.__routes.append(Route(method, path_str, view))

    def resolve(self, method: Method, path: str) -> tuple[Route, dict[str, str]]:
        path_parts = path.strip("/").split("/")
        path_matches = []

        for route in self.__routes:
            pattern_parts = route.path_str.strip("/").split("/")

            if len(pattern_parts) != len(path_parts):
                continue

            params = {}
            matched = True

            for pattern, actual in zip(pattern_parts, path_parts, strict=True):
                if pattern.startswith(":"):
                    params[pattern[1:]] = actual
                elif pattern != actual:
                    matched = False
                    break

            if matched:
                path_matches.append((route, params))

        if not path_matches:
            raise NotFoundError

        for route, params in path_matches:
            if route.method == method.upper():
                return route, params

        allowed = sorted({route.method for route, _ in path_matches})
        raise MethodNotAllowedError(headers={"Allow": ", ".join(allowed)})
