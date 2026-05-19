from APsystemsEZ1 import APsystemsEZ1M
import asyncio
import json
import os
from datetime import datetime
from collections import defaultdict
import paho.mqtt.client as mqtt
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open("config.json") as f:
    config = json.load(f)


def get_time_slot():
    now = datetime.now().timestamp()
    slot = int(now // 600) * 600
    return str(slot)


def load_or_create_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = json.load(f)
            data.setdefault("totals", {})
            return data
    else:
        return {
            "date": datetime.now().strftime("%d/%m/%Y"),
            "totals": {},
            "intervals": {},
        }


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def get_filepath(name):
    filename = f"{name}-{datetime.now().strftime('%Y-%m-%d')}.json"
    return os.path.join(DATA_DIR, filename)


def round_value(value):
    return round(value, 2)


def round_optional(value, digits):
    if value is None:
        return None
    return round(value, digits)


def mark_error(interval, exc):
    interval["error"] = True
    interval["error_type"] = type(exc).__name__
    message = str(exc)
    if message:
        interval["error_message"] = message


def collect_victron(broker_ip, listen_seconds=5):
    values = defaultdict(lambda: None)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if isinstance(payload, dict) and "value" in payload:
                values[msg.topic] = payload["value"]
        except Exception:
            pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(broker_ip, 1883)
    client.subscribe("N/#")
    client.loop_start()

    portal_id = None
    deadline = time.monotonic() + listen_seconds
    while time.monotonic() < deadline:
        for topic in values.keys():
            parts = topic.split("/")
            if len(parts) > 1:
                portal_id = parts[1]
                break
        if portal_id:
            break
        time.sleep(0.1)

    if not portal_id:
        client.loop_stop()
        client.disconnect()
        return None

    client.publish(f"R/{portal_id}/keepalive", "")
    time.sleep(listen_seconds)
    client.loop_stop()
    client.disconnect()

    def topic_path(path):
        return f"N/{portal_id}/{path}"

    def get_value(data, path, default=None):
        return data.get(path, default)

    grid_w = get_value(values, topic_path("system/0/Ac/Grid/L1/Power"))
    load_w = get_value(values, topic_path("system/0/Ac/Consumption/L1/Power"))
    pv_w = get_value(values, topic_path("system/0/Ac/PvOnOutput/L1/Power"))
    if pv_w is None:
        pv_w = get_value(values, topic_path("pvinverter/31/Ac/Power"))

    battery_power_raw = get_value(values, topic_path("system/0/Dc/Battery/Power"))
    battery_w = -battery_power_raw if battery_power_raw is not None else None
    battery_v = get_value(values, topic_path("system/0/Dc/Battery/Voltage"))
    battery_a = get_value(values, topic_path("system/0/Dc/Battery/Current"))
    battery_soc = get_value(values, topic_path("battery/512/Soc"))

    return {
        "grid_w": round_optional(grid_w, 1),
        "load_w": round_optional(load_w, 1),
        "pv_w": round_optional(pv_w, 1),
        "battery_w": round_optional(battery_w, 1),
        "battery_v": round_optional(battery_v, 2),
        "battery_a": round_optional(battery_a, 2),
        "battery_soc": round_optional(battery_soc, 1),
    }


async def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    slot = get_time_slot()

    for name, inverter_config in config["inversores"].items():
        filepath = get_filepath(name)
        data = load_or_create_json(filepath)

        data["intervals"][slot] = {
            "iso_time": datetime.fromtimestamp(int(slot)).isoformat(),
        }

        inverter = APsystemsEZ1M(inverter_config["ip"], inverter_config["port"])

        try:
            response = await inverter.get_output_data()
            if response is None:
                raise TimeoutError("No response from inverter")

            data["totals"] = {
                "p1": round_value(response.e1 * 1000),
                "p2": round_value(response.e2 * 1000),
            }

            data["intervals"][slot].update(
                {
                    "p1": round_value(response.p1),
                    "p2": round_value(response.p2),
                    "total_w": round_value(response.p1 + response.p2),
                }
            )

        except Exception as exc:
            mark_error(data["intervals"][slot], exc)

        save_json(filepath, data)

    victron_config = config.get("victron", {})

    victron_units = {}
    if "ip" in victron_config:
        victron_units["victron"] = victron_config
    else:
        victron_units = victron_config

    VICTRON_METRICS = {
        "red": "grid_w",
        "consumo": "load_w",
        "fv": "pv_w",
        "bateria": "battery_w",
        "bateria-tension": "battery_v",
        "bateria-corriente": "battery_a",
        "bateria-soc": "battery_soc",
    }

    for name, vc in victron_units.items():
        victron_error = None
        try:
            snapshot = await asyncio.to_thread(collect_victron, vc["ip"])
            if snapshot is None:
                raise TimeoutError("No MQTT values received from Victron")
        except Exception as exc:
            snapshot = None
            victron_error = exc

        for metric_name, key in VICTRON_METRICS.items():
            filepath = get_filepath(f"{name}-{metric_name}")
            data = load_or_create_json(filepath)
            data["intervals"][slot] = {
                "iso_time": datetime.fromtimestamp(int(slot)).isoformat(),
            }

            if snapshot is None or snapshot.get(key) is None:
                mark_error(
                    data["intervals"][slot],
                    victron_error or KeyError(f"Missing Victron metric {key}"),
                )
            else:
                data["intervals"][slot]["value"] = snapshot[key]

            save_json(filepath, data)


asyncio.run(main())
