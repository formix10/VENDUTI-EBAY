import os
import tempfile
import unittest
from unittest.mock import patch
from collector import number, normalize_items
from storage import connect, monthly_calls

class ParsingTests(unittest.TestCase):
    def test_prices(self):
        self.assertEqual(number("€ 1.234,50"), 1234.50)
        self.assertEqual(number("1,234.50"), 1234.50)
        self.assertEqual(number({"value": "19,90"}), 19.90)
        self.assertIsNone(number(True))
        self.assertIsNone(number("n/d"))

    def test_items(self):
        self.assertEqual(len(normalize_items({"data": {"items": [{"title": "DS"}]}})), 1)
        self.assertEqual(normalize_items({"data": []}), [])

class StorageTests(unittest.TestCase):
    def test_starts_empty_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"DB_PATH": os.path.join(folder, "sales.sqlite3")}):
                with connect() as con:
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM categories").fetchone()[0], 0)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0)
                    self.assertEqual(monthly_calls(con), 0)
                    con.execute("INSERT INTO categories(id,name,min_price) VALUES('1','Console',20)")
                    values = ("1", "item-1", "Nintendo DS", 30, "EUR", "2026-01-01", "", "", "2026-01-02")
                    query = """INSERT OR IGNORE INTO sales
                    (category_id,external_id,title,price,currency,sold_at,url,image_url,captured_at)
                    VALUES(?,?,?,?,?,?,?,?,?)"""
                    con.execute(query, values)
                    con.execute(query, values)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 1)

if __name__ == "__main__":
    unittest.main()
