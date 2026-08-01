"""
Amo de Llaves — Bot de Telegram para monitorización energética.

Comandos:
  /estado   — Potencias en tiempo real (último intervalo disponible)
  /hoy      — Resumen de producción y consumo del día
  /ayer     — Resumen del día anterior
  /alertas  — Cosas que requieren atención AHORA
  /semana   — Resumen de los últimos 7 días

Monitorización proactiva:
  Cada 10 minutos revisa anomalías y envía alertas automáticas si detecta:
  - Dispositivos caídos (APSystems offline, Victron sin datos)
  - Producción anormalmente baja respecto a la media
  - Excedentes solares que podrías aprovechar
"""

import asyncio
import json
import os
import sys
import tomllib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# ── paths ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_TOML = BASE_DIR / "config.toml"

# ── helpers ────────────────────────────────────────────────────────

def load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def load_config() -> dict:
    if CONFIG_TOML.exists():
        with open(CONFIG_TOML, "rb") as f:
            return tomllib.load(f)
    return {}


def load_daily(date_str: str) -> dict | None:
    path = DATA_DIR / f"daily-{date_str}.json"
    if path.exists():
        return load_json(path)
    # fallback: try to assemble from raw files
    files = sorted(DATA_DIR.glob(f"*-{date_str}.json"))
    if not files:
        return None
    devices = {}
    for fp in files:
        if fp.name.startswith("daily-"):
            continue
        name = fp.name[: -len(f"-{date_str}.json")]
        try:
            devices[name] = load_json(fp)
        except Exception:
            pass
    return {"date": date_str, "devices": devices}


def load_history() -> list[dict]:
    path = DATA_DIR / "history.json"
    if path.exists():
        return load_json(path)
    return []


def latest_value(device_data: dict) -> float | None:
    """Get the last numeric value from a device's intervals."""
    intervals = device_data.get("intervals", {})
    if not intervals:
        return None
    sorted_keys = sorted(intervals.keys(), reverse=True)
    for key in sorted_keys:
        entry = intervals[key]
        if "error" in entry:
            continue
        # Try 'value' first (victron), then 'total_w', then p1+p2
        if "value" in entry and isinstance(entry["value"], (int, float)):
            return entry["value"]
        if "total_w" in entry and isinstance(entry["total_w"], (int, float)):
            return entry["total_w"]
        if "p1" in entry and "p2" in entry:
            p1 = entry["p1"] if isinstance(entry["p1"], (int, float)) else 0
            p2 = entry["p2"] if isinstance(entry["p2"], (int, float)) else 0
            if p1 > 0 or p2 > 0:
                return p1 + p2
    return None


def latest_timestamp(device_data: dict) -> str | None:
    """Get the ISO timestamp of the last interval."""
    intervals = device_data.get("intervals", {})
    if not intervals:
        return None
    sorted_keys = sorted(intervals.keys(), reverse=True)
    for key in sorted_keys:
        entry = intervals[key]
        if "iso_time" in entry:
            return entry["iso_time"]
    return None


def format_watts(w: float | None) -> str:
    if w is None:
        return "—"
    w = abs(w)
    if w >= 1000:
        return f"{w/1000:.1f} kW"
    return f"{w:.0f} W"


def format_wh(wh: float | None) -> str:
    if wh is None:
        return "—"
    if wh >= 1000:
        return f"{wh/1000:.2f} kWh"
    return f"{wh:.0f} Wh"


def format_pct(pct: float | None) -> str:
    if pct is None:
        return "—"
    return f"{pct:.0f}%"


def format_celsius(c: float | None) -> str:
    if c is None:
        return "—"
    return f"{c:.1f}°C"


def device_health(device_data: dict) -> str:
    """Return 🟢/🟡/🔴 for a device's health."""
    intervals = device_data.get("intervals", {})
    if not intervals:
        return "🔴"
    errors = 0
    total = len(intervals)
    for entry in intervals.values():
        if "error" in entry:
            errors += 1
    if errors == total:
        return "🔴"
    if errors > total * 0.3:
        return "🟡"
    # Check recency
    ts = latest_timestamp(device_data)
    if ts:
        try:
            last = datetime.fromisoformat(ts)
            ago = datetime.now(timezone.utc) - last
            if ago > timedelta(hours=2):
                return "🔴"
            if ago > timedelta(minutes=30):
                return "🟡"
        except Exception:
            pass
    return "🟢"


# ── comandos ───────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏰 *Amo de Llaves* a su servicio.\n\n"
        "Comandos disponibles:\n"
        "/estado — Potencias ahora mismo\n"
        "/hoy — Resumen del día\n"
        "/ayer — Resumen de ayer\n"
        "/alertas — Problemas detectados\n"
        "/semana — Últimos 7 días",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Snapshot de potencias en tiempo real (último intervalo)."""
    today = datetime.now().strftime("%Y-%m-%d")
    daily = load_daily(today)

    if not daily:
        await update.message.reply_text("❌ No hay datos disponibles para hoy.")
        return

    devices = daily.get("devices", {})

    # ── Producción ──
    prod_lines = []
    total_prod = 0

    for dev_id in ["goodwe1", "apsystems1", "apsystems2", "apsystems3"]:
        if dev_id not in devices:
            continue
        lv = latest_value(devices[dev_id])
        ts = latest_timestamp(devices[dev_id])
        health = device_health(devices[dev_id])
        name = dev_id.replace("1", " 1").replace("2", " 2").replace("3", " 3")
        if lv is not None:
            total_prod += lv
        hour = ts[-8:-3] if ts and len(ts) > 8 else "?"
        prod_lines.append(f"  {health} {name}: {format_watts(lv)}  ({hour})")

    # Victron FV
    victron_fv = devices.get("victron1-fv")
    if victron_fv:
        lv = latest_value(victron_fv)
        ts = latest_timestamp(victron_fv)
        health = device_health(victron_fv)
        hour = ts[-8:-3] if ts and len(ts) > 8 else "?"
        if lv is not None:
            total_prod += lv
        prod_lines.append(f"  {health} Victron FV: {format_watts(lv)}  ({hour})")

    # ── Consumo / Red / Batería ──
    consumo = latest_value(devices.get("victron1-consumo", {}))
    red = latest_value(devices.get("victron1-red", {}))
    bateria = latest_value(devices.get("victron1-bateria", {}))
    soc = latest_value(devices.get("victron1-bateria-soc", {}))
    temp = latest_value(devices.get("victron1-bateria-temperatura", {}))

    # Net balance
    if total_prod is not None and consumo is not None:
        balance = total_prod - consumo
        balance_str = (
            f"⚡ {format_watts(abs(balance))} a red" if balance > 0
            else f"🔌 {format_watts(abs(balance))} de red"
        )
    else:
        balance_str = ""

    msg = (
        f"⚡ *ESTADO AHORA*\n\n"
        f"☀️ *Producción:* {format_watts(total_prod)}\n"
    )
    msg += "\n".join(prod_lines) + "\n\n"
    msg += (
        f"🏠 *Consumo casa:* {format_watts(consumo)}\n"
        f"🔌 *Red (Iberdrola):* {format_watts(red)}\n"
    )
    if bateria is not None or soc is not None:
        msg += f"🔋 *Batería:* {format_watts(bateria)} | SOC: {format_pct(soc)} | {format_celsius(temp)}\n"
    if balance_str:
        msg += f"\n{balance_str}"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resumen de producción y consumo del día."""
    today = datetime.now().strftime("%Y-%m-%d")
    daily = load_daily(today)

    if not daily:
        await update.message.reply_text("❌ No hay datos para hoy aún.")
        return

    devices = daily.get("devices", {})

    # Producción desde history
    history = load_history()
    today_entry = next((h for h in history if h["date"] == today), None)

    msg = f"📊 *HOY* ({today[5:]})\n\n"

    if today_entry:
        msg += f"☀️ Producción total: *{format_wh(today_entry['total_wh'])}*\n\n"
        inv = today_entry.get("inverters", {})
        for dev_id in ["goodwe1", "apsystems1", "apsystems2", "apsystems3"]:
            if dev_id in inv:
                health = device_health(devices.get(dev_id, {}))
                name = dev_id.replace("1", " 1").replace("2", " 2").replace("3", " 3")
                msg += f"  {health} {name}: {format_wh(inv[dev_id])}\n"
    else:
        # Try to compute from device totals directly
        msg += "☀️ *Producción (desde dispositivos):*\n"
        total = 0
        for dev_id in ["goodwe1", "apsystems1", "apsystems2", "apsystems3"]:
            if dev_id in devices:
                totals = devices[dev_id].get("totals", {})
                p1 = totals.get("p1", 0) or 0
                p2 = totals.get("p2", 0) or 0
                wh = p1 + p2
                if wh > 0:
                    total += wh
                    health = device_health(devices[dev_id])
                    name = dev_id.replace("1", " 1").replace("2", " 2").replace("3", " 3")
                    msg += f"  {health} {name}: {format_wh(wh)}\n"
        msg += f"\n  Total: *{format_wh(total)}*\n"

    msg += "\n🏠 *Consumo (último):*\n"
    for dev_id, label in [
        ("victron1-consumo", "Casa"),
        ("victron1-red", "Red"),
    ]:
        if dev_id in devices:
            lv = latest_value(devices[dev_id])
            health = device_health(devices[dev_id])
            msg += f"  {health} {label}: {format_watts(lv)}\n"

    if "victron1-bateria-soc" in devices:
        soc = latest_value(devices["victron1-bateria-soc"])
        msg += f"\n🔋 Batería SOC: {format_pct(soc)}"

    # Comparativa con ayer
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yest_entry = next((h for h in history if h["date"] == yesterday), None)
    if today_entry and yest_entry and yest_entry["total_wh"] > 0:
        diff = today_entry["total_wh"] - yest_entry["total_wh"]
        diff_pct = (diff / yest_entry["total_wh"]) * 100
        arrow = "📈" if diff > 0 else "📉"
        msg += f"\n\n{arrow} vs ayer: {diff_pct:+.0f}%"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_ayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    history = load_history()
    entry = next((h for h in history if h["date"] == yesterday), None)

    if not entry:
        await update.message.reply_text(f"❌ No hay datos para {yesterday}.")
        return

    msg = f"📊 *AYER* ({yesterday[5:]})\n\n"
    msg += f"☀️ Producción total: *{format_wh(entry['total_wh'])}*\n\n"
    inv = entry.get("inverters", {})
    for dev_id, label in [
        ("goodwe1", "GoodWe"),
        ("apsystems1", "APSystems 1"),
        ("apsystems2", "APSystems 2"),
        ("apsystems3", "APSystems 3"),
    ]:
        if dev_id in inv:
            msg += f"  {label}: {format_wh(inv[dev_id])}\n"

    # Best day
    all_days = sorted(history, key=lambda h: h["total_wh"], reverse=True)
    rank = next((i+1 for i, h in enumerate(all_days) if h["date"] == yesterday), None)
    if rank:
        total_days = len(all_days)
        msg += f"\n🏆 Ranking histórico: #{rank} de {total_days} días"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta y reporta problemas actuales."""
    today = datetime.now().strftime("%Y-%m-%d")
    daily = load_daily(today)
    alerts = []

    if not daily:
        await update.message.reply_text("❌ No hay datos para analizar hoy.")
        return

    devices = daily.get("devices", {})

    # 1. APSystems offline
    for dev_id in ["apsystems1", "apsystems2", "apsystems3"]:
        if dev_id in devices:
            health = device_health(devices[dev_id])
            if health != "🟢":
                name = dev_id.replace("1", " 1").replace("2", " 2").replace("3", " 3")
                # Check last successful reading
                intervals = devices[dev_id].get("intervals", {})
                last_ok = None
                for key in sorted(intervals.keys(), reverse=True):
                    if "error" not in intervals[key]:
                        last_ok = intervals[key].get("iso_time", "?")
                        break
                alerts.append((health, f"{name}: sin datos desde {last_ok}" if last_ok else f"{name}: sin datos"))

    # 2. Victron sin datos
    for dev_id in ["victron1-consumo", "victron1-fv"]:
        if dev_id in devices:
            health = device_health(devices[dev_id])
            if health == "🔴":
                name = dev_id.replace("victron1-", "")
                alerts.append((health, f"Victron {name}: sin datos recientes"))

    # 3. Producción baja vs media
    history = load_history()
    today_entry = next((h for h in history if h["date"] == today), None)
    if today_entry and len(history) >= 3:
        recent = [h for h in history if h["date"] != today][-10:]
        if recent:
            avg = sum(h["total_wh"] for h in recent) / len(recent)
            if today_entry["total_wh"] < avg * 0.5 and today_entry["total_wh"] > 0:
                alerts.append(("🟡", f"Producción baja: {format_wh(today_entry['total_wh'])} vs media {format_wh(avg)}"))
            elif today_entry["total_wh"] == 0:
                alerts.append(("🔴", "¡Producción CERO hoy!"))

    # 4. Excedente solar
    fv = latest_value(devices.get("victron1-fv", {}))
    consumo = latest_value(devices.get("victron1-consumo", {}))
    red = latest_value(devices.get("victron1-red", {}))
    if fv and consumo and red is not None and fv > 0:
        balance = fv - consumo
        if balance > 500 and red < 0:  # vertiendo más de 500W
            alerts.append(("💡", f"Excedente solar: {format_watts(balance)} vertiendo. ¡Buen momento para lavadora/termo/lavarplatos!"))

    # 5. Consumo vampiro nocturno
    hour = datetime.now().hour
    if 0 <= hour < 6 and consumo and consumo > 300:
        alerts.append(("🟡", f"Consumo nocturno alto: {format_watts(consumo)} (¿algo encendido?)"))

    if not alerts:
        await update.message.reply_text("✅ *Todo en orden.*\nNo se detectan problemas ahora mismo.", parse_mode=ParseMode.MARKDOWN)
        return

    msg = "🚨 *ALERTAS*\n\n"
    for icon, text in alerts:
        msg += f"{icon} {text}\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resumen de los últimos 7 días."""
    history = load_history()
    if not history:
        await update.message.reply_text("❌ No hay histórico disponible.")
        return

    last_7 = history[-7:]

    msg = "📅 *ÚLTIMOS 7 DÍAS*\n\n"
    total_wh = 0
    for day in last_7:
        date = day["date"][5:]  # MM-DD
        wh = day["total_wh"]
        total_wh += wh
        # Barra simple
        bar_len = min(int(wh / 1000), 20)  # 1 char per kWh, max 20
        bar = "▓" * bar_len + "░" * (20 - bar_len)
        msg += f"`{date}` {bar} {format_wh(wh)}\n"

    avg = total_wh / len(last_7) if last_7 else 0
    msg += f"\n📊 Total: *{format_wh(total_wh)}* | Media: *{format_wh(avg)}/día*"

    best = max(last_7, key=lambda h: h["total_wh"])
    worst = min(last_7, key=lambda h: h["total_wh"])
    msg += f"\n🔝 Mejor: {best['date'][5:]} ({format_wh(best['total_wh'])})"
    msg += f"\n🔻 Peor: {worst['date'][5:]} ({format_wh(worst['total_wh'])})"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Bot error: {context.error}", file=sys.stderr)


# ── monitorización proactiva ───────────────────────────────────────

async def monitor_loop(application: Application, chat_id: int):
    """
    Cada 10 minutos revisa el sistema y envía alertas si detecta problemas.
    Solo envía alertas que no haya enviado recientemente (evita spam).
    """
    last_alerts: dict[str, datetime] = {}  # alert type -> last sent
    cooldown = timedelta(hours=2)  # no repetir alerta antes de 2h

    while True:
        try:
            await asyncio.sleep(600)  # cada 10 minutos

            today = datetime.now().strftime("%Y-%m-%d")
            daily = load_daily(today)
            if not daily:
                continue

            devices = daily.get("devices", {})
            now = datetime.now()
            new_alerts = []

            # 1. APSystems caídos (solo alerta si lleva más de 1h caído)
            for dev_id in ["apsystems1", "apsystems2", "apsystems3"]:
                if dev_id not in devices:
                    continue
                intervals = devices[dev_id].get("intervals", {})
                if not intervals:
                    continue
                # encontrar el último sin error
                last_ok_ts = None
                for key in sorted(intervals.keys(), reverse=True):
                    entry = intervals[key]
                    if "error" not in entry:
                        last_ok_ts = entry.get("iso_time")
                        break
                if last_ok_ts:
                    try:
                        last_ok = datetime.fromisoformat(last_ok_ts)
                        if now - last_ok > timedelta(hours=1):
                            name = dev_id.replace("1", " 1").replace("2", " 2").replace("3", " 3")
                            alert_key = f"offline-{dev_id}"
                            if alert_key not in last_alerts or now - last_alerts[alert_key] > cooldown:
                                hours_off = (now - last_ok).total_seconds() / 3600
                                new_alerts.append(f"🔴 {name}: sin datos desde hace {hours_off:.0f}h")
                                last_alerts[alert_key] = now
                    except Exception:
                        pass

            # 2. Día de producción cero
            history = load_history()
            today_entry = next((h for h in history if h["date"] == today), None)
            if today_entry and today_entry["total_wh"] == 0 and datetime.now().hour > 10:
                alert_key = "zero-production"
                if alert_key not in last_alerts or now - last_alerts[alert_key] > cooldown:
                    new_alerts.append("🔴 ¡ALERTA! Producción CERO hoy. ¿Falló el colector de datos?")
                    last_alerts[alert_key] = now

            # 3. Excedente solar significativo (> 1kW vertiendo)
            fv = latest_value(devices.get("victron1-fv", {}))
            consumo_val = latest_value(devices.get("victron1-consumo", {}))
            red_val = latest_value(devices.get("victron1-red", {}))
            if fv and consumo_val and red_val is not None and fv > 0:
                balance = fv - consumo_val
                if balance > 1000 and red_val < 0:
                    alert_key = "excedente"
                    if alert_key not in last_alerts or now - last_alerts[alert_key] > timedelta(hours=4):
                        new_alerts.append(f"💡 Excedente solar: {format_watts(balance)} vertiendo a red. ¡Aprovecha para consumir!")
                        last_alerts[alert_key] = now

            # Enviar alertas
            for alert in new_alerts:
                try:
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=f"🚨 *Alerta automática*\n\n{alert}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception as e:
                    print(f"Error enviando alerta: {e}", file=sys.stderr)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error en monitor loop: {e}", file=sys.stderr)
            await asyncio.sleep(60)


# ── main ───────────────────────────────────────────────────────────

def main():
    # Config from env or toml
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id_str = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        cfg = load_config()
        tg = cfg.get("telegram", {})
        token = tg.get("bot_token", "")
        chat_id_str = str(tg.get("chat_id", ""))

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN no configurado.", file=sys.stderr)
        print("   Ponlo en config.toml [telegram] o exporta TELEGRAM_BOT_TOKEN", file=sys.stderr)
        sys.exit(1)

    if not chat_id_str:
        print("❌ TELEGRAM_CHAT_ID no configurado.", file=sys.stderr)
        print("   Ponlo en config.toml [telegram] o exporta TELEGRAM_CHAT_ID", file=sys.stderr)
        sys.exit(1)

    chat_id = int(chat_id_str)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(CommandHandler("hoy", cmd_hoy))
    app.add_handler(CommandHandler("ayer", cmd_ayer))
    app.add_handler(CommandHandler("alertas", cmd_alertas))
    app.add_handler(CommandHandler("semana", cmd_semana))
    app.add_error_handler(error_handler)

    # Lanzar monitor proactivo en background
    loop = asyncio.get_event_loop()
    monitor_task = loop.create_task(monitor_loop(app, chat_id))

    print(f"🏰 Amo de Llaves iniciado. Chat ID: {chat_id}")
    print("   Comandos: /estado /hoy /ayer /alertas /semana")

    try:
        app.run_polling()
    finally:
        monitor_task.cancel()


if __name__ == "__main__":
    main()
