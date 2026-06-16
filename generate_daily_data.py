import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
METADATA_FILE = DATA_DIR / "metadata.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aglutina los JSON diarios de una fecha en data/daily-YYYY-MM-DD.json."
    )
    parser.add_argument("date", help="Fecha a procesar en formato YYYY-MM-DD")
    return parser.parse_args()


def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("La fecha debe tener formato YYYY-MM-DD.") from error

    return value


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"El archivo {path} debe contener un objeto JSON.")

    return data


def get_daily_files(target_date: str) -> list[Path]:
    return sorted(
        path
        for path in DATA_DIR.glob(f"*-{target_date}.json")
        if path.name != f"daily-{target_date}.json"
    )


def get_device_id(path: Path, target_date: str) -> str:
    suffix = f"-{target_date}.json"
    if not path.name.endswith(suffix):
        raise ValueError(f"Nombre de archivo no esperado: {path.name}")

    return path.name[: -len(suffix)]


def load_metadata() -> dict[str, Any] | None:
    if not METADATA_FILE.exists():
        return None

    return load_json(METADATA_FILE)


def get_expected_device_ids(metadata: dict[str, Any] | None) -> list[str]:
    if not metadata:
        return []

    ids: list[str] = []
    for device in metadata.get("devices", []):
        device_id = device.get("id")
        device_type = device.get("type")
        if not isinstance(device_id, str):
            continue

        if device_type == "victron":
            for sample in device.get("samples", []):
                sample_id = sample.get("id")
                if isinstance(sample_id, str):
                    ids.append(f"{device_id}-{sample_id}")
        else:
            ids.append(device_id)

    return ids


def build_daily_bundle(target_date: str) -> dict[str, Any]:
    daily_files = get_daily_files(target_date)
    if not daily_files:
        raise FileNotFoundError(
            f"No se encontraron archivos diarios para la fecha {target_date} en {DATA_DIR}."
        )

    devices: dict[str, dict[str, Any]] = {}
    skipped_files: list[dict[str, str]] = []
    for path in daily_files:
        try:
            devices[get_device_id(path, target_date)] = load_json(path)
        except (json.JSONDecodeError, ValueError) as error:
            skipped_files.append({"file": path.name, "error": str(error)})

    if not devices:
        raise ValueError(f"No se pudo cargar ningún JSON diario válido para {target_date}.")

    metadata = load_metadata()
    expected_device_ids = get_expected_device_ids(metadata)
    ordered_devices = {
        device_id: devices[device_id]
        for device_id in expected_device_ids
        if device_id in devices
    }
    for device_id in sorted(devices):
        ordered_devices.setdefault(device_id, devices[device_id])

    return {
        "date": target_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
        "skipped_files": skipped_files,
        "devices": ordered_devices,
    }


def save_daily_bundle(target_date: str, bundle: dict[str, Any]) -> Path:
    output_path = DATA_DIR / f"daily-{target_date}.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(bundle, file, indent=2)
        file.write("\n")

    return output_path


def main() -> None:
    args = parse_args()
    target_date = validate_date(args.date)
    bundle = build_daily_bundle(target_date)
    save_daily_bundle(target_date, bundle)


if __name__ == "__main__":
    main()
