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

- **collect.py** — Consulta los inversores en la red local y SEMS Portal cada 10 min, y guarda JSONs diarios por dispositivo.
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

## Licencia

Uso personal.
