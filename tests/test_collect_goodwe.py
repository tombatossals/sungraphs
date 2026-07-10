"""Tests for GoodWe SEMS value extraction."""

import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collect import (  # noqa: E402
    build_victron_latest_device,
    get_nearest_vrm_point,
    get_recoverable_vrm_points,
    get_goodwe_reading,
    get_vrm_recovery_status,
    interval_needs_recovery,
    normalize_vrm_timestamp,
    get_victron_sample_value,
    split_goodwe_daily_wh,
)


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


class TestGetVictronSampleValue(unittest.TestCase):
    def test_uses_first_available_topic(self):
        sample = {
            "id": "bateria-temperatura",
            "topics": [
                "system/0/Dc/Battery/Temperature",
                "battery/512/Dc/0/Temperature",
            ],
            "digits": 1,
        }
        values = {"N/portal/battery/512/Dc/0/Temperature": 27.26}

        self.assertEqual(get_victron_sample_value(values, "portal", sample), 27.3)


class TestVictronVrmRecovery(unittest.TestCase):
    def test_normalizes_vrm_millisecond_timestamps(self):
        self.assertEqual(normalize_vrm_timestamp(1783634400000), 1783634400)

    def test_builds_points_with_multiplier_and_source_time(self):
        sample = {
            "id": "bateria",
            "vrm_attribute": "Pb",
            "multiplier": -1,
            "digits": 1,
        }
        records = {"Pb": [[1783634400000, -123.44]]}

        points = get_recoverable_vrm_points(records, sample)

        self.assertEqual(points["1783634400"]["timestamp"], 1783634400)
        self.assertEqual(points["1783634400"]["value"], 123.4)
        self.assertIn("T", points["1783634400"]["source_time"])

    def test_finds_nearest_vrm_point_for_ten_minute_slot(self):
        points = {
            "1783634400": {"timestamp": 1783634400, "value": 10},
            "1783635300": {"timestamp": 1783635300, "value": 20},
        }

        self.assertEqual(get_nearest_vrm_point(points, "1783635000")["value"], 20)
        self.assertIsNone(get_nearest_vrm_point(points, "1783636200", max_distance=60))

    def test_only_recovers_missing_error_or_empty_values(self):
        self.assertTrue(interval_needs_recovery(None))
        self.assertTrue(interval_needs_recovery({"error": True}))
        self.assertTrue(interval_needs_recovery({"iso_time": "2026-07-10T00:00:00"}))
        self.assertFalse(interval_needs_recovery({"value": 0}))

    def test_reports_missing_vrm_recovery_config(self):
        status = get_vrm_recovery_status({"samples": [{"id": "fv"}]})

        self.assertFalse(status["enabled"])
        self.assertIn("vrm_site_id", status["missing"])
        self.assertIn("vrm_attribute en al menos una muestra", status["missing"])


class TestBuildVictronLatestDevice(unittest.TestCase):
    def test_builds_latest_snapshot_with_values_and_labels(self):
        device = {"label": "Victron"}
        samples = [
            {"id": "bateria-corriente", "label": "Corriente batería"},
            {"id": "bateria-temperatura", "label": "Temperatura batería"},
        ]
        latest = build_victron_latest_device(
            "victron1",
            device,
            samples,
            {"bateria-corriente": -12.34, "bateria-temperatura": 27.3},
            "1782902400",
        )

        self.assertEqual(latest["id"], "victron1")
        self.assertEqual(latest["label"], "Victron")
        self.assertEqual(latest["slot"], "1782902400")
        self.assertEqual(
            latest["readings"]["bateria-corriente"],
            {
                "id": "bateria-corriente",
                "label": "Corriente batería",
                "value": -12.34,
            },
        )

    def test_marks_missing_sample_as_error(self):
        samples = [{"id": "bateria-temperatura"}]
        latest = build_victron_latest_device(
            "victron1",
            {},
            samples,
            {"bateria-temperatura": None},
            "1782902400",
        )

        reading = latest["readings"]["bateria-temperatura"]
        self.assertTrue(reading["error"])
        self.assertEqual(reading["error_type"], "KeyError")
        self.assertIn("Missing Victron sample bateria-temperatura", reading["error_message"])


if __name__ == "__main__":
    unittest.main()
