"""Tests for Shelly Pro 3EM HTTP RPC collection."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collect import (  # noqa: E402
    collect_shelly_em_snapshot,
    get_shelly_em_value,
    save_metadata,
)


class TestGetShellyEmValue(unittest.TestCase):
    def test_extracts_act_power(self):
        sample = {"id": "criticas", "em_id": 1, "digits": 1}
        payload = {"id": 1, "act_power": 571.1}

        self.assertEqual(get_shelly_em_value(payload, sample), 571.1)

    def test_applies_multiplier(self):
        sample = {"id": "bateria", "em_id": 0, "multiplier": -1, "digits": 1}
        payload = {"id": 0, "act_power": 226.7}

        self.assertEqual(get_shelly_em_value(payload, sample), -226.7)

    def test_rounds_to_digits(self):
        sample = {"id": "secundarias", "em_id": 0, "digits": 2}
        payload = {"id": 0, "act_power": 226.746}

        self.assertEqual(get_shelly_em_value(payload, sample), 226.75)

    def test_returns_none_on_missing_field(self):
        sample = {"id": "aac", "em_id": 2, "digits": 1}
        payload = {"id": 2}

        self.assertIsNone(get_shelly_em_value(payload, sample))

    def test_returns_none_on_non_numeric(self):
        sample = {"id": "aac", "em_id": 2, "digits": 1}
        payload = {"id": 2, "act_power": "no"}

        self.assertIsNone(get_shelly_em_value(payload, sample))

    def test_uses_custom_field(self):
        sample = {"id": "criticas", "em_id": 1, "field": "current", "digits": 1}
        payload = {"id": 1, "current": 3.433}

        self.assertEqual(get_shelly_em_value(payload, sample), 3.4)


class TestCollectShellyEmSnapshot(unittest.TestCase):
    def _fake_urlopen(self, payload):
        response = Mock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        return context

    def test_collects_all_samples(self):
        device = {
            "ip": "192.168.5.25",
            "samples": [
                {"id": "criticas", "em_id": 1, "digits": 1},
                {"id": "secundarias", "em_id": 0, "digits": 1},
                {"id": "aac", "em_id": 2, "digits": 1},
            ],
        }
        payloads = {
            1: {"id": 1, "act_power": 571.1},
            0: {"id": 0, "act_power": -226.7},
            2: {"id": 2, "act_power": 407.5},
        }

        def fake_urlopen(request, timeout=5):
            em_id = int(request.full_url.split("id=")[1])
            return self._fake_urlopen(payloads[em_id])

        with patch("collect.urlopen", side_effect=fake_urlopen):
            readings = collect_shelly_em_snapshot(device)

        self.assertEqual(readings["criticas"], 571.1)
        self.assertEqual(readings["secundarias"], -226.7)
        self.assertEqual(readings["aac"], 407.5)

    def test_raises_timeout_error_when_all_channels_fail(self):
        device = {
            "ip": "192.168.5.25",
            "samples": [{"id": "criticas", "em_id": 1, "digits": 1}],
        }

        def fake_urlopen(request, timeout=5):
            raise TimeoutError("timed out")

        with patch("collect.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(TimeoutError):
                collect_shelly_em_snapshot(device)


class TestSaveMetadataShelly(unittest.TestCase):
    def test_includes_shelly_samples(self):
        from collect import config

        with tempfile.TemporaryDirectory() as tmp:
            metadata_file = Path(tmp) / "metadata.json"
            with patch("collect.METADATA_FILE", str(metadata_file)):
                save_metadata()

            metadata = json.loads(metadata_file.read_text())
            shelly = next(
                device for device in metadata["devices"] if device["id"] == "shelly1"
            )

        self.assertEqual(shelly["type"], "shelly_em")
        self.assertEqual(
            [sample["id"] for sample in shelly["samples"]],
            ["criticas", "secundarias", "aac"],
        )
        self.assertEqual(
            [sample["label"] for sample in shelly["samples"]],
            ["Cargas críticas", "Cargas secundarias", "Aires acondicionados"],
        )


if __name__ == "__main__":
    unittest.main()
