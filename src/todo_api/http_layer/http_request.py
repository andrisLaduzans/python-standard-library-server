import json
from http.client import HTTPMessage
from urllib.parse import parse_qs, urlsplit

from todo_api.error import InvalidJsonError
from todo_api.http_layer.http_method import Method


class HttpRequest:
    def __init__(
        self,
        method: Method,
        target: str,
        headers: HTTPMessage | None = None,
        body: bytes = b"",
        auth: str | None = None,
    ):
        self.method = method
        self.target = target
        self.headers = headers if headers is not None else HTTPMessage()
        self.body = body
        self.auth = auth
        self.user_id: str | None = None

    @property
    def path(self) -> str:
        return urlsplit(self.target).path

    @property
    def query(self) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.target).query)

    def json(self) -> dict:
        try:
            return json.loads(self.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise InvalidJsonError from error
