import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_daily_data import (  # noqa: E402
    build_daily_bundle,
    get_device_id,
    get_expected_device_ids,
    validate_date,
)


class TestValidateDate(unittest.TestCase):
    def test_valid_date(self):
        self.assertEqual(validate_date("2026-06-14"), "2026-06-14")

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            validate_date("14/06/2026")


class TestGetDeviceId(unittest.TestCase):
    def test_extracts_device_id(self):
        path = Path("/fake/data/victron1-bateria-soc-2026-06-14.json")
        self.assertEqual(get_device_id(path, "2026-06-14"), "victron1-bateria-soc")

    def test_raises_on_unexpected_name(self):
        with self.assertRaises(ValueError):
            get_device_id(Path("/fake/data/history.json"), "2026-06-14")


class TestGetExpectedDeviceIds(unittest.TestCase):
    def test_expands_victron_samples(self):
        metadata = {
            "devices": [
                {"id": "goodwe1", "type": "goodwe_sems"},
                {
                    "id": "victron1",
                    "type": "victron",
                    "samples": [{"id": "fv"}, {"id": "consumo"}],
                },
            ]
        }

        self.assertEqual(
            get_expected_device_ids(metadata),
            ["goodwe1", "victron1-fv", "victron1-consumo"],
        )


class TestBuildDailyBundle(unittest.TestCase):
    def test_builds_daily_bundle_ordered_by_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            metadata_file = data_dir / "metadata.json"
            metadata_file.write_text(json.dumps({
                "devices": [
                    {"id": "goodwe1", "type": "goodwe_sems", "label": "GoodWe"},
                    {
                        "id": "victron1",
                        "type": "victron",
                        "samples": [{"id": "consumo", "label": "Consumo"}],
                    },
                ]
            }))
            (data_dir / "victron1-consumo-2026-06-14.json").write_text(
                json.dumps({"date": "14/06/2026", "intervals": {"1": {"value": 300}}})
            )
            (data_dir / "goodwe1-2026-06-14.json").write_text(
                json.dumps({"date": "14/06/2026", "totals": {"p1": 10}, "intervals": {}})
            )

            with patch("generate_daily_data.DATA_DIR", data_dir), patch(
                "generate_daily_data.METADATA_FILE", metadata_file
            ):
                bundle = build_daily_bundle("2026-06-14")

        self.assertEqual(bundle["date"], "2026-06-14")
        self.assertEqual(list(bundle["devices"].keys()), ["goodwe1", "victron1-consumo"])
        self.assertEqual(bundle["metadata"]["devices"][0]["id"], "goodwe1")

    def test_raises_on_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("generate_daily_data.DATA_DIR", Path(tmp)):
                with self.assertRaises(FileNotFoundError):
                    build_daily_bundle("2026-06-14")


if __name__ == "__main__":
    unittest.main()
