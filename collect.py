import asyncio
import argparse
import json
import os
import tomllib
from datetime import datetime, time as datetime_time, timezone
from collections import defaultdict
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_TOML = os.path.join(BASE_DIR, "config.toml")
CONFIG_JSON = os.path.join(BASE_DIR, "config.json")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.json")
VICTRON_FILE = os.path.join(DATA_DIR, "victron.json")

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
    {
        "id": "bateria-temperatura",
        "topics": [
            "system/0/Dc/Battery/Temperature",
            "battery/512/Dc/0/Temperature",
        ],
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


def get_time_slot(timestamp=None):
    now = datetime.now().timestamp() if timestamp is None else timestamp
    slot = int(now // 600) * 600
    return str(slot)


def get_local_date(target_date=None):
    if target_date is not None:
        return target_date
    return datetime.now().date()


def get_day_start_slot(target_date=None):
    day = get_local_date(target_date)
    start = datetime.combine(day, datetime_time.min).timestamp()
    return int(start // 600) * 600


def get_day_slots(current_slot, target_date=None):
    start_slot = get_day_start_slot(target_date)
    end_slot = int(current_slot)
    return [str(slot) for slot in range(start_slot, end_slot + 1, 600)]


def get_json_date(target_date=None):
    day = get_local_date(target_date)
    return day.strftime("%d/%m/%Y")


def load_or_create_json(filename, target_date=None):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = json.load(f)
            data.setdefault("totals", {})
            return data
    else:
        return {
            "date": get_json_date(target_date),
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


def get_filepath(name, target_date=None):
    day = get_local_date(target_date)
    filename = f"{name}-{day.strftime('%Y-%m-%d')}.json"
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


def get_goodwe_mppt_power(section, index):
    voltage = first_number(section.get(f"vpv{index}"))
    current = first_number(section.get(f"ipv{index}"))
    if voltage is None or current is None:
        return None
    return voltage * current


def split_goodwe_daily_wh(daily_wh, p1, p2):
    if daily_wh is None:
        return (0, 0)

    mppt_total = (p1 or 0) + (p2 or 0)
    if mppt_total <= 0:
        return (daily_wh, 0)

    p1_daily = daily_wh * (p1 or 0) / mppt_total
    return (p1_daily, daily_wh - p1_daily)


def mark_error(interval, exc):
    interval["error"] = True
    interval["error_type"] = type(exc).__name__
    message = str(exc)
    if message:
        interval["error_message"] = message


def get_error_payload(exc):
    payload = {
        "error": True,
        "error_type": type(exc).__name__,
    }
    message = str(exc)
    if message:
        payload["error_message"] = message
    return payload


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


def get_vrm_token(device_config):
    token = device_config.get("vrm_token")
    if token:
        return token

    token_env = device_config.get("vrm_token_env", "VICTRON_VRM_TOKEN")
    return os.environ.get(token_env) or os.environ.get("VRM_TOKEN")


def get_vrm_sample_attributes(sample):
    if "vrm_attributes" in sample:
        return sample["vrm_attributes"]
    if "vrm_attribute" in sample:
        return [sample["vrm_attribute"]]
    return []


def get_vrm_recovery_config(device_config):
    site_id = device_config.get("vrm_site_id") or device_config.get("site_id")
    token = get_vrm_token(device_config)
    if not site_id or not token:
        return None

    samples = device_config.get("samples", DEFAULT_VICTRON_SAMPLES)
    attributes = []
    for sample in samples:
        for attribute in get_vrm_sample_attributes(sample):
            if attribute not in attributes:
                attributes.append(attribute)

    if not attributes:
        return None

    return {"site_id": str(site_id), "token": token, "attributes": attributes}


def get_vrm_recovery_status(device_config):
    site_id = device_config.get("vrm_site_id") or device_config.get("site_id")
    token = get_vrm_token(device_config)
    samples = device_config.get("samples", DEFAULT_VICTRON_SAMPLES)
    attributes = []
    sample_count = 0
    for sample in samples:
        sample_attributes = get_vrm_sample_attributes(sample)
        if sample_attributes:
            sample_count += 1
        for attribute in sample_attributes:
            if attribute not in attributes:
                attributes.append(attribute)

    missing = []
    if not site_id:
        missing.append("vrm_site_id")
    if not token:
        token_env = device_config.get("vrm_token_env", "VICTRON_VRM_TOKEN")
        missing.append(f"{token_env} env var")
    if not attributes:
        missing.append("vrm_attribute en al menos una muestra")

    return {
        "enabled": not missing,
        "missing": missing,
        "site_id": str(site_id) if site_id else None,
        "attribute_count": len(attributes),
        "sample_count": sample_count,
    }


def fetch_vrm_stats(site_id, token, attributes, start, end, timeout=20):
    query = [
        ("type", "custom"),
        ("interval", "15mins"),
        ("start", str(start)),
        ("end", str(end)),
    ]
    for attribute in attributes:
        query.append(("attributeCodes[]", attribute))

    url = (
        f"https://vrmapi.victronenergy.com/v2/installations/{site_id}/stats?"
        + urlencode(query)
    )
    request = Request(url, headers={"x-authorization": f"Token {token}"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_vrm_data_attributes(token, timeout=20):
    request = Request(
        "https://vrmapi.victronenergy.com/v2/data-attributes",
        headers={"x-authorization": f"Token {token}"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def iter_matching_vrm_attributes(attributes, query=None):
    query_text = query.lower() if query else None
    for attribute_id, attribute in sorted(
        attributes.items(), key=lambda item: item[1].get("code", item[0])
    ):
        text = " ".join(
            str(attribute.get(key, ""))
            for key in ("code", "description", "formatWithUnit", "dataType")
        )
        if query_text and query_text not in text.lower():
            continue
        yield attribute_id, attribute


def get_vrm_records(stats_response):
    records = stats_response.get("records", {})
    if isinstance(records, dict):
        return records
    return {}


def get_vrm_series(records, attribute):
    series = records.get(attribute)
    if isinstance(series, list):
        return series
    return []


def normalize_vrm_timestamp(timestamp):
    value = float(timestamp)
    if value > 10_000_000_000:
        value = value / 1000
    return int(value)


def get_recoverable_vrm_points(records, sample):
    points = {}
    for attribute in get_vrm_sample_attributes(sample):
        for point in get_vrm_series(records, attribute):
            if not isinstance(point, list) or len(point) < 2:
                continue
            timestamp = normalize_vrm_timestamp(point[0])
            value = to_float(point[1])
            if value is None:
                continue

            slot = get_time_slot(timestamp)
            multiplier = sample.get("multiplier", 1)
            digits = sample.get("digits", 1)
            points[slot] = {
                "timestamp": timestamp,
                "value": round_optional(value * multiplier, digits),
                "source_time": datetime.fromtimestamp(timestamp).isoformat(),
            }
        if points:
            break
    return points


def interval_needs_recovery(interval):
    if not interval:
        return True
    return interval.get("error") or interval.get("value") is None


def get_nearest_vrm_point(points, slot, max_distance=600):
    if slot in points:
        return points[slot]

    target = int(slot)
    nearest = None
    nearest_distance = None
    for point in points.values():
        distance = abs(int(point["timestamp"]) - target)
        if distance <= max_distance and (
            nearest_distance is None or distance < nearest_distance
        ):
            nearest = point
            nearest_distance = distance
    return nearest


def has_victron_day_gaps(name, samples, current_slot, target_date=None):
    slots = get_day_slots(current_slot, target_date)
    for sample in samples:
        filepath = get_filepath(f"{name}-{sample['id']}", target_date)
        if not os.path.exists(filepath):
            return True
        data = load_or_create_json(filepath, target_date)
        intervals = data.get("intervals", {})
        if any(interval_needs_recovery(intervals.get(slot)) for slot in slots):
            return True
    return False


def recover_victron_day_from_vrm(name, device_config, current_slot, target_date=None):
    recovery_config = get_vrm_recovery_config(device_config)
    if not recovery_config:
        return 0

    samples = device_config.get("samples", DEFAULT_VICTRON_SAMPLES)
    if not has_victron_day_gaps(name, samples, current_slot, target_date):
        return 0

    start = get_day_start_slot(target_date)
    end = int(current_slot) + 600
    stats_response = fetch_vrm_stats(
        recovery_config["site_id"],
        recovery_config["token"],
        recovery_config["attributes"],
        start,
        end,
        device_config.get("vrm_timeout", 20),
    )
    records = get_vrm_records(stats_response)
    recovered = 0

    for sample in samples:
        sample_id = sample["id"]
        points = get_recoverable_vrm_points(records, sample)
        if not points:
            continue

        filepath = get_filepath(f"{name}-{sample_id}", target_date)
        data = load_or_create_json(filepath, target_date)
        intervals = data.setdefault("intervals", {})

        for slot in get_day_slots(current_slot, target_date):
            if int(slot) < start or int(slot) > int(current_slot):
                continue
            if not interval_needs_recovery(intervals.get(slot)):
                continue
            point = get_nearest_vrm_point(points, slot)
            if not point:
                continue

            intervals[slot] = {
                "iso_time": datetime.fromtimestamp(int(slot)).isoformat(),
                "value": point["value"],
                "source": "vrm_recovery",
                "source_time": point["source_time"],
            }
            recovered += 1

        save_json(filepath, data)

    return recovered


def build_victron_latest_device(
    name,
    device_config,
    samples,
    snapshot,
    slot,
    victron_error=None,
):
    readings = {}
    for sample in samples:
        sample_id = sample["id"]
        reading = {
            "id": sample_id,
            "label": sample.get("label", sample_id),
        }

        value = snapshot.get(sample_id) if snapshot else None
        if value is None:
            reading.update(
                get_error_payload(
                    victron_error or KeyError(f"Missing Victron sample {sample_id}")
                )
            )
        else:
            reading["value"] = value

        readings[sample_id] = reading

    return {
        "id": name,
        "label": device_config.get("label", name),
        "slot": slot,
        "iso_time": datetime.fromtimestamp(int(slot)).isoformat(),
        "readings": readings,
    }


def load_victron_latest():
    if not os.path.exists(VICTRON_FILE):
        return {"devices": {}}

    try:
        with open(VICTRON_FILE, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {"devices": {}}

    if not isinstance(data, dict):
        return {"devices": {}}

    data.setdefault("devices", {})
    if not isinstance(data["devices"], dict):
        data["devices"] = {}
    return data


def save_victron_latest(name, device_latest):
    latest = load_victron_latest()
    latest["generated_at"] = datetime.now(timezone.utc).isoformat()
    latest["devices"][name] = device_latest
    save_json(VICTRON_FILE, latest)


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

    save_victron_latest(
        name,
        build_victron_latest_device(
            name,
            device_config,
            samples,
            snapshot,
            slot,
            victron_error,
        ),
    )

    try:
        recovered = await asyncio.to_thread(
            recover_victron_day_from_vrm,
            name,
            device_config,
            slot,
        )
        if recovered:
            print(f"Recovered {recovered} Victron intervals from VRM for {name}")
    except Exception as exc:
        print(f"Error recovering Victron intervals from VRM for {name}: {exc}")


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
    mppt1_w = first_number(
        get_goodwe_mppt_power(inverter_data, 1),
        get_goodwe_mppt_power(inverter_full, 1),
    )
    mppt2_w = first_number(
        get_goodwe_mppt_power(inverter_data, 2),
        get_goodwe_mppt_power(inverter_full, 2),
    )

    return {
        "pac": pac,
        "daily_wh": daily_kwh * 1000 if daily_kwh is not None else None,
        "total_kwh": total_kwh,
        "mppt1_w": mppt1_w,
        "mppt2_w": mppt2_w,
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

        daily_wh = reading["daily_wh"] or 0
        total_w = round_value(reading["pac"] or 0)
        p1 = reading["mppt1_w"] if reading["mppt1_w"] is not None else total_w
        p2 = reading["mppt2_w"] if reading["mppt2_w"] is not None else 0
        p1_daily, p2_daily = split_goodwe_daily_wh(daily_wh, p1, p2)

        data["totals"] = {
            "p1": round_value(p1_daily),
            "p2": round_value(p2_daily),
        }
        if reading["total_kwh"] is not None:
            data["total_kwh"] = round_value(reading["total_kwh"])

        interval = data["intervals"][slot]
        interval.update(
            {
                "p1": round_value(p1),
                "p2": round_value(p2),
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


def parse_args():
    parser = argparse.ArgumentParser(description="Colecta datos solares diarios.")
    parser.add_argument(
        "--recover-victron-day",
        nargs="?",
        const=datetime.now().strftime("%Y-%m-%d"),
        help="Recupera huecos Victron de una fecha YYYY-MM-DD usando VRM y sale.",
    )
    parser.add_argument(
        "--list-vrm-attributes",
        nargs="?",
        const="",
        metavar="QUERY",
        help="Lista códigos de atributos VRM; opcionalmente filtra por texto.",
    )
    return parser.parse_args()


def parse_target_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


async def recover_victron_devices_for_day(target_date):
    os.makedirs(DATA_DIR, exist_ok=True)
    save_metadata()

    if target_date == datetime.now().date():
        current_slot = get_time_slot()
    else:
        current_slot = str(get_day_start_slot(target_date) + (24 * 60 * 60) - 600)

    for device_config in config["devices"]:
        if device_config["type"] != "victron":
            continue
        name = device_config["id"]
        status = get_vrm_recovery_status(device_config)
        if not status["enabled"]:
            missing = ", ".join(status["missing"])
            print(f"Skipping VRM recovery for {name}: missing {missing}")
            continue

        recovered = await asyncio.to_thread(
            recover_victron_day_from_vrm,
            name,
            device_config,
            current_slot,
            target_date,
        )
        print(f"Recovered {recovered} Victron intervals from VRM for {name}")


def list_vrm_attributes(query):
    token = os.environ.get("VICTRON_VRM_TOKEN") or os.environ.get("VRM_TOKEN")
    if not token:
        raise ValueError("Falta VICTRON_VRM_TOKEN o VRM_TOKEN en el entorno.")

    attributes = fetch_vrm_data_attributes(token)
    matches = list(iter_matching_vrm_attributes(attributes, query or None))
    if not matches:
        print("No VRM attributes matched.")
        return

    for attribute_id, attribute in matches:
        code = attribute.get("code", attribute_id)
        description = attribute.get("description", "")
        unit = attribute.get("formatWithUnit", "")
        suffix = f" | {unit}" if unit else ""
        print(f"{code}: {description}{suffix}")


async def main():
    args = parse_args()
    if args.list_vrm_attributes is not None:
        list_vrm_attributes(args.list_vrm_attributes)
        return

    if args.recover_victron_day:
        await recover_victron_devices_for_day(parse_target_date(args.recover_victron_day))
        return

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
