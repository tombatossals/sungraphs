"""Tests for generate_history.py (uses unittest for broad compatibility)"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_history import (  # noqa: E402
    validate_date,
    load_history,
    upsert_history_entry,
    build_history_entry,
    get_inverter_name,
    get_inverter_total_wh,
)


class TestValidateDate(unittest.TestCase):
    def test_valid_date(self):
        self.assertEqual(validate_date("2026-05-03"), "2026-05-03")

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            validate_date("not-a-date")


class TestLoadHistory(unittest.TestCase):
    def test_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonexistent.json"
            with patch("generate_history.HISTORY_FILE", path):
                self.assertEqual(load_history(), [])

    def test_loads_list(self):
        data = [{"date": "2026-05-03", "total_wh": 100}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with patch("generate_history.HISTORY_FILE", path):
                self.assertEqual(load_history(), data)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_raises_on_non_list(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"not": "a list"}, f)
            f.flush()
            path = Path(f.name)

        try:
            with patch("generate_history.HISTORY_FILE", path):
                with self.assertRaises(ValueError):
                    load_history()
        finally:
            Path(path).unlink(missing_ok=True)


class TestUpsertHistoryEntry(unittest.TestCase):
    def test_adds_new_entry(self):
        history = [{"date": "2026-05-03", "total_wh": 100}]
        entry = {"date": "2026-05-04", "total_wh": 200}
        result = upsert_history_entry(history, entry)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[-1]["date"], "2026-05-04")

    def test_updates_existing_entry(self):
        history = [{"date": "2026-05-03", "total_wh": 100}]
        entry = {"date": "2026-05-03", "total_wh": 150}
        result = upsert_history_entry(history, entry)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total_wh"], 150)

    def test_sorts_by_date(self):
        entry_a = {"date": "2026-05-10", "total_wh": 100}
        entry_b = {"date": "2026-05-03", "total_wh": 200}
        result = upsert_history_entry([entry_a], entry_b)
        self.assertEqual(result[0]["date"], "2026-05-03")
        self.assertEqual(result[1]["date"], "2026-05-10")


class TestGetInverterName(unittest.TestCase):
    def test_extracts_name(self):
        path = Path("/fake/data/apsystems1-2026-05-03.json")
        self.assertEqual(get_inverter_name(path, "2026-05-03"), "apsystems1")

    def test_raises_on_unexpected_format(self):
        path = Path("/fake/data/badname.json")
        with self.assertRaises(ValueError):
            get_inverter_name(path, "2026-05-03")


class TestGetInverterTotalWh(unittest.TestCase):
    def test_sums_p1_p2(self):
        daily = {"totals": {"p1": 1000, "p2": 500}}
        self.assertEqual(get_inverter_total_wh(daily), 1500.0)

    def test_handles_missing_keys(self):
        daily = {"totals": {}}
        self.assertEqual(get_inverter_total_wh(daily), 0.0)


class TestBuildHistoryEntry(unittest.TestCase):
    def test_raises_on_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            with patch("generate_history.DATA_DIR", data_dir):
                with self.assertRaises(FileNotFoundError):
                    build_history_entry("2026-05-03")

    def test_builds_entry_from_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            inverter_file = data_dir / "inv1-2026-05-03.json"
            inverter_file.write_text(json.dumps({"totals": {"p1": 1000, "p2": 500}}))

            with patch("generate_history.DATA_DIR", data_dir):
                entry = build_history_entry("2026-05-03")
                self.assertEqual(entry["date"], "2026-05-03")
                self.assertEqual(entry["total_wh"], 1500.0)
                self.assertEqual(entry["inverters"], {"inv1": 1500.0})


if __name__ == "__main__":
    unittest.main()
