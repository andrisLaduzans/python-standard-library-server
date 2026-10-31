import tempfile
import unittest
from pathlib import Path

from todo_api.db.database import Database


class TestStore(unittest.TestCase):
    def _init_database(self, db_file_name: str):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / db_file_name)
        self.database.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
