import argparse

from todo_api.config import load_db_path
from todo_api.db.database import Database
from todo_api.db.token_store import TokenStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an API token for a user")
    parser.add_argument("user_id")
    args = parser.parse_args()

    database = Database(load_db_path())
    database.initialize()

    token = TokenStore(database).create(args.user_id)
    print(token)


if __name__ == "__main__":
    main()
