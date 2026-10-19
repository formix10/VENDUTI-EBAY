"""Offline smoke tests: no SoldComps calls and no API key needed."""
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from collector import normalize_items, number, collect
from storage import connect, monthly_calls


class OfflineTests(unittest.TestCase):
    def test_number_formats(self):
        self.assertEqual(number("€ 12,50"), 12.5)
        self.assertEqual(number("1.234,56 €"), 1234.56)
        self.assertIsNone(number(True))

    def test_payload_normalization(self):
        self.assertEqual(normalize_items({"data": {"items": [{"id": "x"}]}}), [{"id": "x"}])
        self.assertEqual(normalize_items({"items": []}), [])

    def test_empty_database_and_category(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"DB_PATH": str(Path(directory) / "test.sqlite3"),
                                         "SOLDCOMPS_API_KEY": "offline-test-key"}):
                with connect() as con:
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM categories").fetchone()[0], 0)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0)
                    self.assertEqual(monthly_calls(con), 0)
                    con.execute("INSERT INTO categories(id,name,min_price,enabled) VALUES(?,?,?,1)",
                                ("139971", "Test console", 70.0))
                    con.commit()
                with patch("collector.requests.get") as get:
                    get.return_value.ok = True
                    get.return_value.status_code = 200
                    get.return_value.json.return_value = {"items": [
                        {"itemId": "sale1", "title": "Console test", "soldPrice": "85,00",
                         "endedAt": "2026-10-01", "soldCurrency": "EUR"},
                        {"itemId": "sale2", "title": "Sotto minimo", "soldPrice": "30,00"}]}
                    self.assertEqual(collect("139971"), (2, 1))
                    self.assertEqual(collect("139971"), (2, 0))
                    self.assertEqual(get.call_count, 2)
                with connect() as con:
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 1)
                    self.assertEqual(monthly_calls(con), 2)


if __name__ == "__main__":
    unittest.main()
