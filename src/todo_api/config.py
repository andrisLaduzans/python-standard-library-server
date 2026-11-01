import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_db_path() -> Path:
    load_dotenv()
    fallback_db_path = Path(__file__).resolve().parent / "todos.db"
    db_path = Path(os.getenv("TODO_DB_PATH", fallback_db_path))
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path
