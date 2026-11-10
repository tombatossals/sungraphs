"""Tests del cliente SEMS+ (API web nueva de GoodWe)."""

import base64
import hashlib
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sems_plus  # noqa: E402
from collect import get_goodwe_reading  # noqa: E402


def factor(code, data=None, unit=None):
    item = {"code": code, "dataType": "NUMERIC"}
    if data is not None:
        item["data"] = data
    if unit:
        item["unit"] = unit
    return item


ALL_STATUS = {
    "total": 1,
    "deviceDetailList": [
        {
            "deviceType": "INVERTER",
            "statusDetailList": [
                {
                    "status": 1,
                    "snList": ["SN123"],
                    "detailMap": {"SN123": {"sn": "SN123", "model": "GW5000D-NS"}},
                }
            ],
        }
    ],
}

TELEMETRY_DAY = [
    {"code": "system", "factors": [factor("sn", "SN123"), factor("Temperature", "41.5", "℃")]},
    {"code": "ac", "factors": [factor("pAc", "2.75", "kW")]},
    {
        "code": "pv",
        "factors": [
            factor("MPPT-1:Ppv", "1.04", "kW"),
            factor("MPPT-2:Ppv", "1.7", "kW"),
            factor("MPPT-1:Vpv", "259.8", "V"),
            factor("MPPT-1:Ipv", "4.0", "A"),
        ],
    },
]

# De noche SEMS+ devuelve los factores sin "data".
TELEMETRY_NIGHT = [
    {"code": "system", "factors": [factor("sn", "SN123"), factor("Temperature", unit="℃")]},
    {"code": "ac", "factors": [factor("pAc", unit="kW")]},
    {"code": "pv", "factors": [factor("MPPT-1:Ppv", unit="kW"), factor("MPPT-2:Ppv", unit="kW")]},
]

TELECOUNTING = [
    {"code": "telecounting_today", "factors": [factor("proPvStatsToday", "10.5", "kWh")]},
    {"code": "telecounting_lifetime", "factors": [factor("proPvStatsTotal", "41234.5", "kWh")]},
]

STATISTICS = {
    "dataList": [
        {
            "item": "proSystemTotalStats",
            "unit": "kWh",
            "statisticsList": [
                {"date": "2026-11-09", "val": 7.2},
                {"date": "2026-11-10", "val": 10.5},
            ],
        }
    ]
}


class FakeClient:
    station_id = "station-1"

    def __init__(self, telemetry=TELEMETRY_DAY, telecounting=TELECOUNTING, all_status=ALL_STATUS):
        self.telemetry = telemetry
        self.telecounting = telecounting
        self.all_status = all_status
        self.calls = []

    def request(self, method, path, params=None, body=None):
        self.calls.append((method, path, params, body))
        if path.endswith("/stations/device/all-status"):
            return self.all_status
        if path.endswith("/telemetry"):
            return self.telemetry
        if path.endswith("/telecounting"):
            return self.telecounting
        if path.endswith("/stations/flow"):
            return {"pAc": 0, "refreshTime": "2026-11-10T12:10:00"}
        if path.endswith("/stations/statistics"):
            return STATISTICS
        raise AssertionError(f"unexpected path {path}")


class TestAuthHelpers(unittest.TestCase):
    def test_password_is_base64_of_md5_hex(self):
        expected = base64.b64encode(hashlib.md5(b"secret").hexdigest().encode()).decode()
        self.assertEqual(sems_plus.encode_password("secret"), expected)

    def test_signature_is_base64_of_sha256_and_timestamp(self):
        signature = sems_plus.build_signature("uid-1", "tok-1", timestamp_ms=1700000000000)
        digest, timestamp = base64.b64decode(signature).decode().split("@")
        self.assertEqual(timestamp, "1700000000000")
        self.assertEqual(
            digest, hashlib.sha256(b"1700000000000@uid-1@tok-1").hexdigest()
        )


class TestFlattenFactors(unittest.TestCase):
    def test_keeps_only_factors_with_data(self):
        factors = sems_plus.flatten_factors(TELEMETRY_NIGHT)
        self.assertEqual(factors, {"sn": "SN123"})

    def test_tolerates_garbage(self):
        self.assertEqual(sems_plus.flatten_factors(None), {})
        self.assertEqual(sems_plus.flatten_factors([None, {"factors": None}]), {})


class TestListInverters(unittest.TestCase):
    def test_returns_inverter_serials_with_status(self):
        inverters = sems_plus.list_inverters(FakeClient())
        self.assertEqual(
            inverters, [{"sn": "SN123", "deviceType": "INVERTER", "status": 1}]
        )

    def test_ignores_other_device_types(self):
        status = {"deviceDetailList": [{"deviceType": "METER", "statusDetailList": [{"snList": ["M1"]}]}]}
        self.assertEqual(sems_plus.list_inverters(FakeClient(all_status=status)), [])


class TestBuildSnapshot(unittest.TestCase):
    def test_daytime_snapshot_feeds_get_goodwe_reading(self):
        snapshot = sems_plus.build_snapshot(FakeClient(), target_date=date(2026, 11, 10))
        reading = get_goodwe_reading(snapshot)

        self.assertEqual(reading["pac"], 2750.0)
        self.assertEqual(reading["daily_wh"], 10500.0)
        self.assertEqual(reading["total_kwh"], 41234.5)
        self.assertAlmostEqual(reading["mppt1_w"], 1040.0)
        self.assertAlmostEqual(reading["mppt2_w"], 1700.0)
        self.assertEqual(reading["temperature"], 41.5)
        self.assertEqual(reading["status"], 1)
        self.assertEqual(reading["sems_time"], "2026-11-10T12:10:00")

    def test_night_snapshot_keeps_daily_total_without_power(self):
        snapshot = sems_plus.build_snapshot(
            FakeClient(telemetry=TELEMETRY_NIGHT), target_date=date(2026, 11, 10)
        )
        reading = get_goodwe_reading(snapshot)

        self.assertIsNone(reading["pac"])
        self.assertIsNone(reading["mppt1_w"])
        self.assertEqual(reading["daily_wh"], 10500.0)

    def test_falls_back_to_station_statistics_for_daily_total(self):
        snapshot = sems_plus.build_snapshot(
            FakeClient(telecounting=[]), target_date=date(2026, 11, 10)
        )
        self.assertEqual(get_goodwe_reading(snapshot)["daily_wh"], 10500.0)

    def test_raises_when_station_has_no_inverters(self):
        with self.assertRaises(sems_plus.SemsPlusError):
            sems_plus.build_snapshot(FakeClient(all_status={"deviceDetailList": []}))


class TestDailyTotals(unittest.TestCase):
    def test_returns_wh_per_day_for_range(self):
        client = FakeClient()
        totals = sems_plus.get_daily_totals_wh(client, date(2026, 11, 9), date(2026, 11, 10))

        self.assertEqual(totals, {"2026-11-09": 7200.0, "2026-11-10": 10500.0})
        _method, _path, _params, body = client.calls[-1]
        self.assertEqual(body["stationId"], "station-1")
        self.assertEqual(body["dimension"], "day")
        self.assertEqual(body["startTime"], "2026-11-09 00:00:00")
        self.assertEqual(body["endTime"], "2026-11-10 23:59:59")


if __name__ == "__main__":
    unittest.main()
