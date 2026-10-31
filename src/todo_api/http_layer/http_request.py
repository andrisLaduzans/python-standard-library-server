import json
from http.client import HTTPMessage


class HttpRequest:
    def __init__(
        self,
        method: str,
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

    def json(self) -> dict:
        return json.loads(self.body)
