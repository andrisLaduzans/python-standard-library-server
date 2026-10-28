import json
from dataclasses import dataclass, field


@dataclass
class HttpResponse:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def json(
        cls, status: int, data: dict | list, headers: dict[str, str] | None = None
    ) -> HttpResponse:
        body = json.dumps(data).encode("utf-8")
        return cls(status, body, headers or {})
