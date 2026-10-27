from dataclasses import dataclass, field


@dataclass
class HttpResponse:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)

"""
same as
class HttpResponse:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None):
        self.status = status
        self.body = body
        self.headers = headers if headers is not None else {}
"""
