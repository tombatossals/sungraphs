import asyncio
import json
import os
import tomllib
from datetime import datetime
from collections import defaultdict
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_TOML = os.path.join(BASE_DIR, "config.toml")
CONFIG_JSON = os.path.join(BASE_DIR, "config.json")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.json")

DEFAULT_VICTRON_SAMPLES = [
    {
        "id": "red",
        "topics": ["system/0/Ac/Grid/L1/Power"],
        "digits": 1,
    },
    {
        "id": "consumo",
        "topics": ["system/0/Ac/Consumption/L1/Power"],
        "digits": 1,
    },
    {
        "id": "fv",
        "topics": [
            "system/0/Ac/PvOnOutput/L1/Power",
            "pvinverter/31/Ac/Power",
        ],
        "digits": 1,
    },
    {
        "id": "bateria",
        "topics": ["system/0/Dc/Battery/Power"],
        "multiplier": -1,
        "digits": 1,
    },
    {
        "id": "bateria-tension",
        "topics": ["system/0/Dc/Battery/Voltage"],
        "digits": 2,
    },
    {
        "id": "bateria-corriente",
        "topics": ["system/0/Dc/Battery/Current"],
        "digits": 2,
    },
    {
        "id": "bateria-soc",
        "topics": ["battery/512/Soc"],
        "digits": 1,
    },
]


def load_config():
    if os.path.exists(CONFIG_TOML):
        with open(CONFIG_TOML, "rb") as f:
            return tomllib.load(f)

    with open(CONFIG_JSON) as f:
        legacy_config = json.load(f)

    devices = []
    for name, inverter_config in legacy_config.get("inversores", {}).items():
        devices.append(
            {
                "id": name,
                "type": inverter_config.get("type", "apsystems"),
                "ip": inverter_config["ip"],
                "port": inverter_config.get("port", 8050),
            }
        )

    victron_config = legacy_config.get("victron", {})
    if "ip" in victron_config:
        devices.append(
            {
                "id": "victron",
                "type": "victron",
                "ip": victron_config["ip"],
                "samples": DEFAULT_VICTRON_SAMPLES,
            }
        )
    else:
        for name, unit_config in victron_config.items():
            devices.append(
                {
                    "id": name,
                    "type": "victron",
                    "ip": unit_config["ip"],
                    "samples": DEFAULT_VICTRON_SAMPLES,
                }
            )

    return {"devices": devices}


config = load_config()


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


def save_metadata():
    metadata = {"devices": []}
    for device in config["devices"]:
        device_metadata = {
            "id": device["id"],
            "type": device["type"],
            "label": device.get("label", device["id"]),
        }
        if device["type"] == "victron":
            device_metadata["samples"] = [
                {
                    "id": sample["id"],
                    "label": sample.get("label", sample["id"]),
                }
                for sample in device.get("samples", DEFAULT_VICTRON_SAMPLES)
            ]
        metadata["devices"].append(device_metadata)

    save_json(METADATA_FILE, metadata)


def get_filepath(name):
    filename = f"{name}-{datetime.now().strftime('%Y-%m-%d')}.json"
    return os.path.join(DATA_DIR, filename)


def round_value(value):
    return round(value, 2)


def round_optional(value, digits):
    if value is None:
        return None
    return round(value, digits)


def to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_number(*values):
    for value in values:
        number = to_float(value)
        if number is not None:
            return number
    return None


def mark_error(interval, exc):
    interval["error"] = True
    interval["error_type"] = type(exc).__name__
    message = str(exc)
    if message:
        interval["error_message"] = message


def get_sample_topics(sample):
    if "topics" in sample:
        return sample["topics"]
    if "topic" in sample:
        return [sample["topic"]]
    return []


def get_victron_sample_value(values, portal_id, sample):
    for topic in get_sample_topics(sample):
        value = values.get(f"N/{portal_id}/{topic}")
        if value is not None:
            multiplier = sample.get("multiplier", 1)
            digits = sample.get("digits", 1)
            return round_optional(value * multiplier, digits)
    return None


def collect_victron(broker_ip, samples, listen_seconds=5):
    import paho.mqtt.client as mqtt

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

    return {
        sample["id"]: get_victron_sample_value(values, portal_id, sample)
        for sample in samples
    }


async def collect_apsystems(name, device_config, slot):
    filepath = get_filepath(name)
    data = load_or_create_json(filepath)

    data["intervals"][slot] = {
        "iso_time": datetime.fromtimestamp(int(slot)).isoformat(),
    }

    try:
        from APsystemsEZ1 import APsystemsEZ1M

        inverter = APsystemsEZ1M(device_config["ip"], device_config.get("port", 8050))
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


async def collect_victron_device(name, device_config, slot):
    samples = device_config.get("samples", DEFAULT_VICTRON_SAMPLES)
    victron_error = None
    try:
        snapshot = await asyncio.to_thread(
            collect_victron,
            device_config["ip"],
            samples,
            device_config.get("listen_seconds", 5),
        )
        if snapshot is None:
            raise TimeoutError("No MQTT values received from Victron")
    except Exception as exc:
        snapshot = None
        victron_error = exc

    for sample in samples:
        sample_id = sample["id"]
        filepath = get_filepath(f"{name}-{sample_id}")
        data = load_or_create_json(filepath)
        data["intervals"][slot] = {
            "iso_time": datetime.fromtimestamp(int(slot)).isoformat(),
        }

        if snapshot is None or snapshot.get(sample_id) is None:
            mark_error(
                data["intervals"][slot],
                victron_error or KeyError(f"Missing Victron sample {sample_id}"),
            )
        else:
            data["intervals"][slot]["value"] = snapshot[sample_id]

        save_json(filepath, data)


def get_first_goodwe_inverter(sems_data):
    inverters = sems_data.get("inverter", [])
    if isinstance(inverters, list) and inverters:
        return inverters[0]
    return {}


def get_goodwe_reading(sems_data):
    kpi = sems_data.get("kpi", {})
    inverter = get_first_goodwe_inverter(sems_data)
    inverter_data = inverter.get("d", {})
    inverter_full = inverter.get("invert_full", {})

    pac = first_number(
        kpi.get("pac"),
        inverter.get("pac"),
        inverter_data.get("pac"),
        inverter_full.get("pac"),
    )
    daily_kwh = first_number(
        inverter.get("eday"),
        inverter_data.get("eDay"),
        inverter_full.get("eday"),
        kpi.get("power"),
    )
    total_kwh = first_number(
        inverter.get("etotal"),
        inverter_data.get("eTotal"),
        inverter_full.get("etotal"),
        kpi.get("total_power"),
    )
    temperature = first_number(
        inverter.get("tempperature"),
        inverter_full.get("tempperature"),
    )

    return {
        "pac": pac,
        "daily_wh": daily_kwh * 1000 if daily_kwh is not None else None,
        "total_kwh": total_kwh,
        "temperature": temperature,
        "status": inverter.get("status", sems_data.get("info", {}).get("status")),
        "sems_time": sems_data.get("info", {}).get("time"),
    }


def collect_goodwe_sems_snapshot(device_config):
    from pygoodwe import API

    goodwe = API(
        system_id=device_config["station_id"],
        account=device_config["account"],
        password=device_config["password"],
    )
    goodwe.getCurrentReadings()
    return goodwe.data


async def collect_goodwe_sems(name, device_config, slot):
    filepath = get_filepath(name)
    data = load_or_create_json(filepath)
    data["intervals"][slot] = {
        "iso_time": datetime.fromtimestamp(int(slot)).isoformat(),
    }

    try:
        sems_data = await asyncio.to_thread(collect_goodwe_sems_snapshot, device_config)
        reading = get_goodwe_reading(sems_data)

        if reading["pac"] is None and reading["daily_wh"] is None:
            raise ValueError("No SEMS production values found")

        daily_wh = round_value(reading["daily_wh"] or 0)
        total_w = round_value(reading["pac"] or 0)

        data["totals"] = {
            "p1": daily_wh,
            "p2": 0,
        }
        if reading["total_kwh"] is not None:
            data["total_kwh"] = round_value(reading["total_kwh"])

        interval = data["intervals"][slot]
        interval.update(
            {
                "p1": total_w,
                "p2": 0,
                "total_w": total_w,
            }
        )
        if reading["temperature"] is not None:
            interval["temperature"] = round_value(reading["temperature"])
        if reading["status"] is not None:
            interval["status"] = reading["status"]
        if reading["sems_time"]:
            interval["sems_time"] = reading["sems_time"]

    except Exception as exc:
        mark_error(data["intervals"][slot], exc)

    save_json(filepath, data)


async def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    save_metadata()

    slot = get_time_slot()

    for device_config in config["devices"]:
        name = device_config["id"]
        device_type = device_config["type"]

        if device_type == "apsystems":
            await collect_apsystems(name, device_config, slot)
        elif device_type == "goodwe_sems":
            await collect_goodwe_sems(name, device_config, slot)
        elif device_type == "victron":
            await collect_victron_device(name, device_config, slot)
        else:
            raise ValueError(f"Unsupported device type: {device_type}")


if __name__ == "__main__":
    asyncio.run(main())
