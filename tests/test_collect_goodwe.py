"""Tests for GoodWe SEMS value extraction."""

import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collect import get_goodwe_reading  # noqa: E402


class TestGetGoodweReading(unittest.TestCase):
    def test_extracts_power_and_daily_energy(self):
        sems_data = {
            "info": {"time": "05/23/2026 09:50:02", "status": 1},
            "kpi": {"pac": 1758.0, "power": 2.3, "total_power": 37143.4},
            "inverter": [
                {
                    "eday": 2.3,
                    "etotal": 37143.4,
                    "status": 1,
                    "tempperature": 31.6,
                    "d": {"pac": 1758.0},
                }
            ],
        }

        reading = get_goodwe_reading(sems_data)

        self.assertEqual(reading["pac"], 1758.0)
        self.assertEqual(reading["daily_wh"], 2300.0)
        self.assertEqual(reading["total_kwh"], 37143.4)
        self.assertEqual(reading["temperature"], 31.6)
        self.assertEqual(reading["status"], 1)
        self.assertEqual(reading["sems_time"], "05/23/2026 09:50:02")

    def test_falls_back_to_kpi_values(self):
        reading = get_goodwe_reading({
            "kpi": {"pac": "120.5", "power": "1.25"},
            "inverter": [],
        })

        self.assertEqual(reading["pac"], 120.5)
        self.assertEqual(reading["daily_wh"], 1250.0)


if __name__ == "__main__":
    unittest.main()
