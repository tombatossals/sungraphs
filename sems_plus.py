"""Cliente mínimo de la API web de SEMS+ (GoodWe).

Desde el 2026-09-23 la API antigua de semsportal.com (la que usa pygoodwe)
devuelve datos vacíos para las plantas migradas a SEMS+. Este módulo habla con
la misma API que usa la web eu-semsplus.goodwe.com. No es una API documentada:
GoodWe puede cambiarla sin avisar.

`build_snapshot` devuelve los datos con la forma del endpoint antiguo
(kpi / inverter / info) para que `collect.get_goodwe_reading` siga sirviendo.
"""

import base64
import hashlib
import json
import time
from datetime import datetime

import requests

LOGIN_HOST = "eu-semsplus.goodwe.com"
LOGIN_PATH = "/web/sems/sems-user/api/v1/auth/cross-login"
DEFAULT_API = "https://eu-gateway.semsportal.com/web/sems"
PLANT_API = "/sems-plant/api"
CLIENT_NAME = "semsPlusWeb"
INVERTER_TYPES = ("INVERTER", "ENERGY_STORAGE_INTEGRATED_CABINET")
SUCCESS_CODES = (0, "0", "00000")
AUTH_ERROR_CODES = ("100001", "100002", "C0602")
TIMEOUT = 15


class SemsPlusError(RuntimeError):
    pass


def encode_password(password):
    """SEMS+ espera base64(md5(password) en hex), no la contraseña en claro."""
    digest = hashlib.md5(password.encode("utf-8")).hexdigest()
    return base64.b64encode(digest.encode("ascii")).decode("ascii")


def build_signature(uid, token, timestamp_ms=None):
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)
    digest = hashlib.sha256(f"{timestamp_ms}@{uid}@{token}".encode("utf-8")).hexdigest()
    return base64.b64encode(f"{digest}@{timestamp_ms}".encode("utf-8")).decode("ascii")


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def flatten_factors(groups):
    """Aplana [{factors: [{code, data}]}] a {code: data}, solo con dato."""
    factors = {}
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, dict):
            continue
        for item in group.get("factors") or []:
            if isinstance(item, dict) and item.get("data") is not None:
                factors[item.get("code")] = item["data"]
    return factors


def error_message(body):
    # Sin volcar el body entero: algunas respuestas de error devuelven las
    # credenciales enviadas.
    for key in ("description", "msg", "message", "error_msg"):
        if body.get(key):
            return str(body[key])
    return "unknown SEMS+ error"


class SemsPlusClient:
    def __init__(self, station_id, account, password, login_host=LOGIN_HOST):
        self.station_id = station_id
        self.account = account
        self.password = password
        self.login_host = login_host
        self.api = DEFAULT_API
        self.session = None

    def login(self):
        anonymous = {
            "uid": "",
            "timestamp": 0,
            "token": "",
            "client": CLIENT_NAME,
            "version": "",
            "language": "en",
        }
        response = requests.post(
            f"https://{self.login_host}{LOGIN_PATH}",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0",
                "Origin": f"https://{self.login_host}",
                "Referer": f"https://{self.login_host}/",
                "token": json.dumps(anonymous),
                "x-signature": build_signature("", ""),
            },
            json={
                "account": self.account,
                "pwd": encode_password(self.password),
                "agreement": 1,
                "isChinese": False,
                "isLocal": False,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("code") not in SUCCESS_CODES:
            raise SemsPlusError(
                f"SEMS+ login failed (code {body.get('code')}): {error_message(body)}"
            )

        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        uid = str(data.get("uid") or "")
        token = str(data.get("token") or "")
        if not uid or not token:
            raise SemsPlusError("SEMS+ login returned no usable session")

        api = body.get("api") or data.get("api")
        if api:
            self.api = str(api).rstrip("/")
        self.session = {
            "uid": uid,
            "timestamp": str(data.get("timestamp") or int(time.time() * 1000)),
            "token": token,
            "client": CLIENT_NAME,
            "version": "",
            "language": "en",
        }

    def request(self, method, path, params=None, body=None):
        """Llama a la API de planta y devuelve el campo `data`."""
        for attempt in (1, 2):
            if self.session is None:
                self.login()

            response = requests.request(
                method,
                self.api + path,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0",
                    "token": json.dumps(self.session),
                    "x-signature": build_signature(
                        self.session["uid"], self.session["token"]
                    ),
                },
                params=params,
                json=body,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()
            code = result.get("code")
            if code in SUCCESS_CODES:
                return result.get("data")
            if str(code) in AUTH_ERROR_CODES and attempt == 1:
                self.session = None
                continue
            raise SemsPlusError(
                f"SEMS+ {path} failed (code {code}): {error_message(result)}"
            )


def list_inverters(client):
    data = client.request(
        "GET",
        f"{PLANT_API}/stations/device/all-status",
        params={"stationId": client.station_id},
    )
    inverters = []
    for group in (data or {}).get("deviceDetailList") or []:
        device_type = group.get("deviceType")
        if device_type not in INVERTER_TYPES:
            continue
        for status_group in group.get("statusDetailList") or []:
            for sn in status_group.get("snList") or []:
                inverters.append(
                    {
                        "sn": sn,
                        "deviceType": device_type,
                        "status": status_group.get("status"),
                    }
                )
    return inverters


def get_device_factors(client, inverter, kind):
    return flatten_factors(
        client.request(
            "GET",
            f"{PLANT_API}/equipments/{inverter['sn']}/{kind}",
            params={"deviceType": inverter["deviceType"], "pwId": client.station_id},
        )
    )


def get_daily_totals_wh(client, start_date, end_date):
    """Producción diaria {YYYY-MM-DD: Wh} de la planta entre dos fechas."""
    data = client.request(
        "POST",
        f"{PLANT_API}/stations/statistics",
        body={
            "stationId": client.station_id,
            "isReport": False,
            "items": ["proSystemTotalStats"],
            "dimension": "day",
            "startTime": f"{start_date:%Y-%m-%d} 00:00:00",
            "endTime": f"{end_date:%Y-%m-%d} 23:59:59",
        },
    )
    totals = {}
    for item in (data or {}).get("dataList") or []:
        if item.get("item") != "proSystemTotalStats":
            continue
        for point in item.get("statisticsList") or []:
            kwh = to_number(point.get("val")) if isinstance(point, dict) else None
            if kwh is not None and point.get("date"):
                totals[point["date"]] = kwh * 1000
    return totals


def kw_to_w(value):
    number = to_number(value)
    return number * 1000 if number is not None else None


def build_snapshot(client, target_date=None):
    """Lectura actual del primer inversor, con la forma del endpoint antiguo."""
    inverters = list_inverters(client)
    if not inverters:
        raise SemsPlusError("SEMS+ returned no inverters for this station")
    inverter = inverters[0]

    telemetry = get_device_factors(client, inverter, "telemetry")
    counters = get_device_factors(client, inverter, "telecounting")

    kpi = {}
    pac = kw_to_w(telemetry.get("pAc"))
    if pac is not None:
        kpi["pac"] = pac

    detail = {}
    for index in (1, 2):
        # get_goodwe_reading calcula la potencia MPPT como vpv * ipv: le damos
        # la potencia en W como "tensión" con corriente 1.
        mppt_w = kw_to_w(telemetry.get(f"MPPT-{index}:Ppv"))
        if mppt_w is not None:
            detail[f"vpv{index}"] = mppt_w
            detail[f"ipv{index}"] = 1

    legacy_inverter = {"status": inverter["status"], "d": detail}
    daily_kwh = to_number(counters.get("proPvStatsToday"))
    if daily_kwh is None:
        day = target_date or datetime.now().date()
        daily_wh = get_daily_totals_wh(client, day, day).get(f"{day:%Y-%m-%d}")
        daily_kwh = daily_wh / 1000 if daily_wh is not None else None
    if daily_kwh is not None:
        legacy_inverter["eday"] = daily_kwh
    total_kwh = to_number(counters.get("proPvStatsTotal"))
    if total_kwh is not None:
        legacy_inverter["etotal"] = total_kwh
    temperature = to_number(telemetry.get("Temperature"))
    if temperature is not None:
        legacy_inverter["tempperature"] = temperature

    info = {}
    try:
        flow = client.request(
            "GET",
            f"{PLANT_API}/stations/flow",
            params={"stationId": client.station_id},
        )
        if isinstance(flow, dict) and flow.get("refreshTime"):
            info["time"] = flow["refreshTime"]
    except (SemsPlusError, requests.exceptions.RequestException, ValueError):
        pass

    return {"kpi": kpi, "inverter": [legacy_inverter], "info": info}
