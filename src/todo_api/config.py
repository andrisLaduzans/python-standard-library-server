import os
from pathlib import Path

from dotenv import load_dotenv


def load_db_path() -> Path:
    load_dotenv()
    fallback_db_path = Path(__file__).resolve().parent / "todos.db"
    db_path = Path(os.getenv("TODO_DB_PATH", fallback_db_path))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path
