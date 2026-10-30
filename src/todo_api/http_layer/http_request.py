import json
from http.client import HTTPMessage


class HttpRequest:
    def __init__(
        self,
        method: str,
        target: str,
        headers: HTTPMessage | None = None,
        body: bytes = b"",
    ):
        self.method = method
        self.target = target
        self.headers = headers if headers is not None else HTTPMessage()
        self.body = body

    def json(self) -> dict:
        return json.loads(self.body)
