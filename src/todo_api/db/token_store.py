import hashlib
import secrets
from contextlib import closing

from todo_api.db.database import Database


class TokenStore:
    def __init__(self, database: Database):
        self._database = database

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)

        with closing(self._database.connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO api_tokens (token_hash, user_id) VALUES (?, ?)",
                    (self._hash(token), user_id),
                )

        return token

    def find_user_id(self, token: str) -> str | None:
        with closing(self._database.connect()) as connection:
            with connection:
                row = connection.execute(
                    "SELECT user_id FROM api_tokens WHERE token_hash = ?",
                    (self._hash(token),),
                ).fetchone()

        return row[0] if row else None
