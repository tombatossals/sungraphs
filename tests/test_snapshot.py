"""Tests for snapshot.py"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from snapshot import (  # noqa: E402
    capture,
    prune_old_days,
    solar_elevation,
    update_index,
)

SECRET_URL = "http://192.0.2.1:88/cgi-bin/CGIProxy.fcgi?cmd=snapPicture2&usr=u&pwd=secret"


class TestSolarElevation(unittest.TestCase):
    def test_solar_elevation_noon_positive(self):
        when = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
        self.assertGreater(solar_elevation(when, 40.0, 0.0), 60)

    def test_solar_elevation_midnight_negative(self):
        when = datetime(2026, 6, 21, 0, 0, tzinfo=timezone.utc)
        self.assertLess(solar_elevation(when, 40.0, 0.0), -6)


class TestUpdateIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.day = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_update_index_appends_sorted(self):
        update_index(self.day, "2026-11-25", "10:20", 1200, "1020.jpg")
        result = update_index(self.day, "2026-11-25", "10:10", 600, "1010.jpg")
        self.assertEqual([i["time"] for i in result["images"]], ["10:10", "10:20"])
        on_disk = json.loads((self.day / "index.json").read_text())
        self.assertEqual(on_disk, result)
        self.assertEqual(on_disk["date"], "2026-11-25")

    def test_update_index_is_world_readable(self):
        update_index(self.day, "2026-11-25", "10:10", 600, "1010.jpg")
        self.assertEqual((self.day / "index.json").stat().st_mode & 0o777, 0o644)

    def test_update_index_replaces_same_time(self):
        update_index(self.day, "2026-11-25", "10:10", 600, "1010.jpg")
        result = update_index(self.day, "2026-11-25", "10:10", 610, "1010.jpg")
        self.assertEqual(len(result["images"]), 1)
        self.assertEqual(result["images"][0]["ts"], 610)

    def test_update_index_recovers_from_corrupt_file(self):
        (self.day / "index.json").write_text("{")
        result = update_index(self.day, "2026-11-25", "10:10", 600, "1010.jpg")
        self.assertEqual(len(result["images"]), 1)


class TestPrune(unittest.TestCase):
    def test_prune_old_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            cam = Path(tmp)
            for name in ("2026-10-01", "2026-11-20", "notadate"):
                (cam / name).mkdir()
                (cam / name / "x.jpg").write_bytes(b"x")
            removed = prune_old_days(cam, date(2026, 11, 25), 30)
            self.assertEqual(removed, ["2026-10-01"])
            self.assertFalse((cam / "2026-10-01").exists())
            self.assertTrue((cam / "2026-11-20").exists())
            self.assertTrue((cam / "notadate").exists())


class TestCapture(unittest.TestCase):
    def test_capture_failure_returns_false_without_url_in_output(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(err), patch(
            "snapshot.requests.get",
            side_effect=requests.ConnectionError(f"failed for {SECRET_URL}"),
        ):
            ok = capture(SECRET_URL, Path(tmp) / "1010.jpg")
        self.assertFalse(ok)
        self.assertNotIn("pwd=", err.getvalue())
        self.assertIn("ConnectionError", err.getvalue())

    def test_capture_rejects_non_jpeg(self):
        resp = MagicMock(status_code=200, content=b"<html>")
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()), patch(
            "snapshot.requests.get", return_value=resp
        ):
            dest = Path(tmp) / "1010.jpg"
            ok = capture(SECRET_URL, dest)
            self.assertFalse(ok)
            self.assertFalse(dest.exists())

    def test_capture_writes_jpeg(self):
        resp = MagicMock(status_code=200, content=b"\xff\xd8fakejpeg")
        with tempfile.TemporaryDirectory() as tmp, patch(
            "snapshot.requests.get", return_value=resp
        ), patch("snapshot.SIPS", None):
            dest = Path(tmp) / "1010.jpg"
            self.assertTrue(capture(SECRET_URL, dest))
            self.assertEqual(dest.read_bytes(), b"\xff\xd8fakejpeg")


if __name__ == "__main__":
    unittest.main()
