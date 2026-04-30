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


def get_filename():
    return datetime.now().strftime("%Y-%m-%d.json")


def load_or_create_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        return {
            "date": datetime.now().strftime("%d/%m/%Y"),
            "intervals": {}
        }


def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def get_filepath():
    filename = datetime.now().strftime("%Y-%m-%d.json")
    return os.path.join(DATA_DIR, filename)

async def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    filepath = get_filepath()
    data = load_or_create_json(filepath)
    slot = get_time_slot()

    # 🔹 Crear o sobrescribir completamente el intervalo
    data["intervals"][slot] = {
        "timestamp_iso": datetime.fromtimestamp(int(slot)).isoformat(),
        "inverters": {}
    }

    for name, inverter_config in config['inversores'].items():
        inverter = APsystemsEZ1M(
            inverter_config['ip'],
            inverter_config['port']
        )

        try:
            response = await inverter.get_output_data()

            data["intervals"][slot]["inverters"][name] = {
                "p1": response.p1,
                "p2": response.p2,
                "total_w": response.p1 + response.p2
            }

        except Exception:
            data["intervals"][slot]["inverters"][name] = {
                "error": True
            }

    save_json(filepath, data)


asyncio.run(main())