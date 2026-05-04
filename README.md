# sungraphs

Monitor solar personal para microinversores **APSystems EZ1**. Colecta datos de producción cada 10 minutos, los almacena como JSON diarios y los visualiza en un dashboard web.

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

- **collect.py** — Consulta los inversores en la red local cada 10 min y guarda JSONs diarios por inversor.
- **generate_history.py** — Agrega los totales diarios en `data/history.json`.
- **collect.sh / generate_history.sh** — Wrappers que ejecutan los scripts, hacen commit y push a Git.
- **frontend/** — App React (Vite + TypeScript) que consume los JSONs como estáticos.

## Requisitos

- Python 3 + `apsystems-ez1` (ver `requirements.txt`)
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

`config.json` — lista de inversores con sus direcciones IP en la LAN.

## Licencia

Uso personal.
