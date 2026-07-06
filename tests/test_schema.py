import unittest
from pathlib import Path


class SchemaInitializationTests(unittest.TestCase):
    def test_schema_is_idempotent(self) -> None:
        schema_sql = Path("schema.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS condominio", schema_sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS usuario", schema_sql)
        self.assertNotIn("DROP TABLE", schema_sql.upper())


if __name__ == "__main__":
    unittest.main()
