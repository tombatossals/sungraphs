#!/usr/bin/env python3
"""Captura un snapshot de la cámara que enfoca a las placas.

Guarda data/camera/YYYY-MM-DD/HHMM.jpg y mantiene data/camera/YYYY-MM-DD/index.json.
La configuración sale de [camera] en config.toml y, por encima, de camera.local.toml
(no versionado, para la URL con credenciales). Nunca imprime la URL.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
CAMERA_DIR = BASE_DIR / "data" / "camera"
CONFIG_FILES = [BASE_DIR / "config.toml", BASE_DIR / "camera.local.toml"]
SIPS = "/usr/bin/sips" if os.path.exists("/usr/bin/sips") else None
MAX_SIZE_PX = 960
MIN_ELEVATION_DEG = -6.0  # crepúsculo civil
DEFAULT_RETENTION_DAYS = 30


def log(msg):
    print(f"[snapshot] {msg}", file=sys.stderr)


def solar_elevation(when, lat, lon):
    """Elevación solar aproximada (NOAA) en grados. `when` debe llevar tz."""
    when = when.astimezone(timezone.utc)
    day_of_year = when.timetuple().tm_yday
    hour = when.hour + when.minute / 60 + when.second / 3600
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    true_solar_minutes = hour * 60 + eqtime + 4 * lon
    hour_angle = math.radians(true_solar_minutes / 4 - 180)
    lat_r = math.radians(lat)
    cos_zenith = math.sin(lat_r) * math.sin(decl) + math.cos(lat_r) * math.cos(decl) * math.cos(hour_angle)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    return 90 - math.degrees(math.acos(cos_zenith))


def _write_json_atomic(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def update_index(day_dir, date_str, time_hhmm, ts, filename):
    day_dir = Path(day_dir)
    index_path = day_dir / "index.json"
    images = []
    try:
        existing = json.loads(index_path.read_text())
        images = [i for i in existing.get("images", []) if isinstance(i, dict)]
    except (OSError, ValueError, AttributeError):
        images = []
    images = [i for i in images if i.get("time") != time_hhmm]
    images.append({"time": time_hhmm, "ts": int(ts), "file": filename})
    images.sort(key=lambda i: i.get("ts", 0))
    index = {"date": date_str, "images": images}
    _write_json_atomic(index_path, index)
    return index


def prune_old_days(camera_dir, today, retention_days):
    camera_dir = Path(camera_dir)
    if not camera_dir.is_dir():
        return []
    cutoff = today - timedelta(days=retention_days)
    removed = []
    for entry in sorted(camera_dir.iterdir()):
        if not entry.is_dir():
            continue
        try:
            day = date.fromisoformat(entry.name)
        except ValueError:
            continue
        if day < cutoff:
            shutil.rmtree(entry)
            removed.append(entry.name)
    return removed


def capture(url, dest, timeout=15):
    dest = Path(dest)
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        # str(exc) puede contener la URL con credenciales: solo el tipo.
        log(f"error al contactar con la cámara: {type(exc).__name__}")
        return False
    if resp.status_code != 200:
        log(f"la cámara respondió HTTP {resp.status_code}")
        return False
    if not resp.content.startswith(b"\xff\xd8"):
        log("la respuesta de la cámara no es un JPEG")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dest.parent, suffix=".jpg")
    with os.fdopen(fd, "wb") as f:
        f.write(resp.content)
    if SIPS:
        result = subprocess.run(
            [SIPS, "-Z", str(MAX_SIZE_PX), tmp], capture_output=True
        )
        if result.returncode != 0:
            log("sips no pudo redimensionar; se guarda el original")
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)
    return True


def load_camera_config():
    config = {}
    for path in CONFIG_FILES:
        if path.exists():
            with open(path, "rb") as f:
                config.update(tomllib.load(f).get("camera", {}))
    return config


def main(argv=None):
    parser = argparse.ArgumentParser(description="Snapshot de la cámara de las placas")
    parser.add_argument("--force", action="store_true", help="capturar aunque sea de noche")
    args = parser.parse_args(argv)

    config = load_camera_config()
    url = config.get("snapshot_url")
    if not url:
        log("sin [camera].snapshot_url configurado; nada que hacer")
        return 0

    now = datetime.now().astimezone()
    lat, lon = config.get("latitude"), config.get("longitude")
    if not args.force and lat is not None and lon is not None:
        if solar_elevation(now, float(lat), float(lon)) < MIN_ELEVATION_DEG:
            return 0

    date_str = now.strftime("%Y-%m-%d")
    filename = now.strftime("%H%M") + ".jpg"
    day_dir = CAMERA_DIR / date_str
    if capture(url, day_dir / filename):
        update_index(day_dir, date_str, now.strftime("%H:%M"), int(now.timestamp()), filename)

    retention = int(config.get("retention_days", DEFAULT_RETENTION_DAYS))
    prune_old_days(CAMERA_DIR, now.date(), retention)
    return 0


if __name__ == "__main__":
    sys.exit(main())
