from contextlib import closing

from tests.utils.test_store import TestStore
from todo_api.db.token_store import TokenStore


class TokenStoreTest(TestStore):
    def setUp(self) -> None:
        self._init_database("tokens.db")
        self.store = TokenStore(self.database)

    def test_created_token_resolves_to_its_user(self):
        token = self.store.create("user-1")
        self.assertEqual("user-1", self.store.find_user_id(token))

    def test_unknown_token_returns_none(self):
        self.assertIsNone(self.store.find_user_id("unknown"))

    def test_raw_token_is_not_stored_in_table(self):
        token = self.store.create("user-1")

        with closing(self.database.connect()) as connection:
            rows = connection.execute("SELECT token_hash FROM api_tokens").fetchall()

        self.assertEqual(1, len(rows))
        self.assertNotIn(token, [token_hash for (token_hash,) in rows])
