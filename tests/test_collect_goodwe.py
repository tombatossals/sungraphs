"""Tests for GoodWe SEMS value extraction."""

import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collect import get_goodwe_reading, split_goodwe_daily_wh  # noqa: E402


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

    def test_extracts_mppt_power_from_voltage_and_current(self):
        reading = get_goodwe_reading({
            "kpi": {"pac": 2688.0, "power": 5.6},
            "inverter": [
                {
                    "d": {
                        "vpv1": 140.4,
                        "ipv1": 7.4,
                        "vpv2": 215.0,
                        "ipv2": 7.9,
                    }
                }
            ],
        })

        self.assertEqual(reading["mppt1_w"], 1038.96)
        self.assertEqual(reading["mppt2_w"], 1698.5)

    def test_splits_daily_energy_by_mppt_power(self):
        p1, p2 = split_goodwe_daily_wh(5600, 1038.96, 1698.5)

        self.assertAlmostEqual(p1, 2125.39, places=2)
        self.assertAlmostEqual(p2, 3474.61, places=2)
        self.assertEqual(round(p1 + p2, 2), 5600)

    def test_falls_back_to_kpi_values(self):
        reading = get_goodwe_reading({
            "kpi": {"pac": "120.5", "power": "1.25"},
            "inverter": [],
        })

        self.assertEqual(reading["pac"], 120.5)
        self.assertEqual(reading["daily_wh"], 1250.0)
        self.assertIsNone(reading["mppt1_w"])
        self.assertIsNone(reading["mppt2_w"])


if __name__ == "__main__":
    unittest.main()
