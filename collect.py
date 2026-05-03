from APsystemsEZ1 import APsystemsEZ1M
import asyncio
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open('config.json') as f:
    config = json.load(f)


def get_time_slot():
    now = datetime.now().timestamp()
    slot = int(now // 600) * 600
    return str(slot)


def load_or_create_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            data.setdefault("totals", {})
            return data
    else:
        return {
            "date": datetime.now().strftime("%d/%m/%Y"),
            "totals": {},
            "intervals": {}
        }


def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


def get_filepath(name):
    filename = f"{name}-{datetime.now().strftime('%Y-%m-%d')}.json"
    return os.path.join(DATA_DIR, filename)


async def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    slot = get_time_slot()

    for name, inverter_config in config['inversores'].items():
        filepath = get_filepath(name)
        data = load_or_create_json(filepath)

        data["intervals"][slot] = {
            "iso_time": datetime.fromtimestamp(int(slot)).isoformat(),
        }

        inverter = APsystemsEZ1M(
            inverter_config['ip'],
            inverter_config['port']
        )

        try:
            response = await inverter.get_output_data()

            data["totals"] = {
                "p1": response.e1 * 1000,
                "p2": response.e2 * 1000,
            }

            data["intervals"][slot].update({
                "p1": response.p1,
                "p2": response.p2,
            })


        except Exception:
            data["intervals"][slot]["error"] = True

        save_json(filepath, data)


asyncio.run(main())