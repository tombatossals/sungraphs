# sungraphs

Monitor solar personal para inversores **APSystems EZ1**, **GoodWe SEMS** y métricas **Victron**. Colecta datos cada 10 minutos, los almacena como JSON diarios y los visualiza en un dashboard web.

## Arquitectura

```
┌──────────────────┐     ┌───────────────┐     ┌───────────────────┐
│  collect.py      │ ──► │  data/*.json  │ ──► │  Frontend React   │
│  (cada 10 min)   │     │  history.json │     │  (Chart.js +      │
│                  │     │               │     │   Tailwind CSS)   │
└──────────────────┘     └───────────────┘     └───────────────────┘
         ▲                        │
         │                   git commit + push
    APSystems EZ1                 │
    (LAN local)            api.micronautas.com
                                 (static files)
```

- **collect.py** — Consulta los inversores en la red local y SEMS Portal cada 10 min, guarda JSONs diarios por dispositivo y actualiza `data/victron.json` con las últimas lecturas Victron.
- **generate_history.py** — Agrega los totales diarios en `data/history.json`.
- **collect.sh / generate_history.sh** — Wrappers que ejecutan los scripts, hacen commit y push a Git.
- **frontend/** — App React (Vite + TypeScript) que consume los JSONs como estáticos.

## Requisitos

- Python 3 + dependencias de `requirements.txt`
- Node.js 20+ (para desarrollar el frontend)

## Uso

```bash
# Colectar datos
python collect.py

# Generar histórico
python generate_history.py YYYY-MM-DD

# Frontend (desarrollo)
cd frontend && npm install && npm run dev

# Frontend (producción)
cd frontend && npm run build
```

## Configuración

`config.toml` — lista de dispositivos. Los APSystems y Victron usan direcciones
IP en la LAN; GoodWe SEMS usa credenciales de portal y `station_id`. Cada
muestra Victron genera un JSON diario con el nombre
`<dispositivo>-<muestra>-YYYY-MM-DD.json`.

Ejemplo GoodWe SEMS:

```toml
[[devices]]
id = "goodwe1"
type = "goodwe_sems"
label = "GoodWe DNS-5000"
account = "usuario@example.com"
password = "..."
station_id = "..."
```

Ejemplo de muestra Victron:

```toml
[[devices.samples]]
id = "fv"
topics = [
  "system/0/Ac/PvOnOutput/L1/Power",
  "pvinverter/31/Ac/Power",
]
digits = 1
```

Las muestras Victron pueden indicar `topic` o una lista `topics`; en ese caso
se usa el primer valor MQTT disponible y se guarda como
`<dispositivo>-<muestra>-YYYY-MM-DD.json`.

### Recuperación Victron desde VRM

Si el GX se queda sin conectividad local pero VRM acaba recibiendo el histórico,
`collect.py` puede rellenar los huecos del día usando la API de VRM. Para
activarlo, añade el id de instalación y el código VRM de cada muestra que quieras
recuperar:

```toml
[[devices]]
id = "victron1"
type = "victron"
ip = "192.168.4.198"
vrm_site_id = "123456"
vrm_token_env = "VICTRON_VRM_TOKEN"

[[devices.samples]]
id = "bateria"
topic = "system/0/Dc/Battery/Power"
vrm_attribute = "Pb"
multiplier = -1
digits = 1
```

El token se lee de `VICTRON_VRM_TOKEN` por defecto, o de la variable indicada en
`vrm_token_env`. También puedes usar `vrm_token` en `config.toml`, aunque es
preferible no guardar secretos en el repo.

La recuperación se ejecuta tras cada recogida Victron si detecta slots del día
sin valor o con error. También se puede lanzar manualmente:

```bash
python collect.py --recover-victron-day 2026-07-10
```

VRM entrega el histórico con intervalo mínimo de 15 minutos; Sungraphs guarda el
punto recuperado en el slot de 10 minutos correspondiente y marca el intervalo
con `source = "vrm_recovery"`.

Además, cada recogida Victron actualiza `data/victron.json` con el último
snapshot de todas sus muestras configuradas. El archivo contiene los equipos
Victron por id, su `slot`, `iso_time` y un mapa `readings` con valores como
temperatura, corriente, tensión o SOC.

## Licencia

Uso personal.
