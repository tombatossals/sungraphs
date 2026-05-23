import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.json"
METADATA_FILE = DATA_DIR / "metadata.json"
PRODUCTION_DEVICE_TYPES = {"apsystems", "goodwe_sems"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera o actualiza data/history.json a partir de los JSON diarios."
    )
    parser.add_argument(
        "date",
        help="Fecha a procesar en formato YYYY-MM-DD",
    )
    return parser.parse_args()


def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("La fecha debe tener formato YYYY-MM-DD.") from error

    return value


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []

    with HISTORY_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("El archivo data/history.json debe contener una lista JSON.")

    return data


def get_daily_files(target_date: str) -> list[Path]:
    return sorted(DATA_DIR.glob(f"*-{target_date}.json"))


def get_inverter_name(path: Path, target_date: str) -> str:
    suffix = f"-{target_date}.json"
    if not path.name.endswith(suffix):
        raise ValueError(f"Nombre de archivo no esperado: {path.name}")

    return path.name[: -len(suffix)]


def get_inverter_total_wh(daily_data: dict[str, Any]) -> float:
    totals = daily_data.get("totals", {})
    p1 = totals.get("p1", 0)
    p2 = totals.get("p2", 0)
    return round(float(p1) + float(p2), 2)


def get_production_device_ids() -> set[str] | None:
    if not METADATA_FILE.exists():
        return None

    metadata = load_json(METADATA_FILE)
    devices = metadata.get("devices", [])
    return {
        device["id"]
        for device in devices
        if device.get("type") in PRODUCTION_DEVICE_TYPES and "id" in device
    }


def build_history_entry(target_date: str) -> dict[str, Any]:
    daily_files = get_daily_files(target_date)
    if not daily_files:
        raise FileNotFoundError(
            f"No se encontraron archivos diarios para la fecha {target_date} en {DATA_DIR}."
        )

    inverter_totals: dict[str, float] = {}
    production_device_ids = get_production_device_ids()

    for path in daily_files:
        daily_data = load_json(path)
        inverter_name = get_inverter_name(path, target_date)
        if production_device_ids is not None and inverter_name not in production_device_ids:
            continue
        inverter_totals[inverter_name] = get_inverter_total_wh(daily_data)

    return {
        "date": target_date,
        "total_wh": round(sum(inverter_totals.values()), 2),
        "inverters": inverter_totals,
    }


def upsert_history_entry(history: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    filtered_history = [item for item in history if item.get("date") != entry["date"]]
    filtered_history.append(entry)
    filtered_history.sort(key=lambda item: item.get("date", ""))
    return filtered_history


def save_history(history: list[dict[str, Any]]) -> None:
    with HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2)
        file.write("\n")


def main() -> None:
    args = parse_args()
    target_date = validate_date(args.date)
    history = load_history()
    entry = build_history_entry(target_date)
    updated_history = upsert_history_entry(history, entry)
    save_history(updated_history)


if __name__ == "__main__":
    main()
