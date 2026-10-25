from collections.abc import Callable
from enum import StrEnum
from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit


class Routes:
    class Todos(StrEnum):
        todos = "/todos"
        todos_id = f"{todos}/:id"

        @classmethod
        def with_id(cls, todo_id: str) -> str:
            return cls.todos_id.replace(":id", todo_id)


class Route:
    def __init__(self, method: str, path_str: Routes.Todos, action: Callable | None):
        self.method = method
        self.path_str = path_str
        self.action = action

    def __str__(self) -> Routes.Todos:
        return self.path_str

    def to_dict(self) -> dict:
        return {"method": self.method, "path": self.path_str}


class Router:
    def __init__(self):
        self.__routes: list[Route] = []

    def add_route(self, method: str, path_str: Routes.Todos, action: Callable) -> None:
        self.__routes.append(Route(method.upper(), path_str, action))

    def resolve(
        self, method: str, url_str: str
    ) -> tuple[Route | None, dict, dict, int, list[str]]:
        url = urlsplit(url_str)
        query = parse_qs(url.query)
        method = method.upper()

        path_matches = []

        for route in self.__routes:
            pattern_parts = route.path_str.strip("/").split("/")
            path_parts = url.path.strip("/").split("/")

            if len(pattern_parts) != len(path_parts):
                continue

            params = {}
            matched = True

            for pattern, actual in zip(pattern_parts, path_parts, strict=True):
                if pattern.startswith(":"):
                    parsed_pattern = pattern[1:]
                    params[parsed_pattern] = actual
                elif pattern != actual:
                    matched = False
                    break

            if matched:
                path_matches.append((route, params))

        if not path_matches:
            return None, {}, query, HTTPStatus.NOT_FOUND, []

        for route, params in path_matches:
            if route.method == method:
                return route, params, query, HTTPStatus.OK, []

        allowed_methods = sorted({route.method for route, _ in path_matches})
        return None, {}, query, HTTPStatus.METHOD_NOT_ALLOWED, allowed_methods
