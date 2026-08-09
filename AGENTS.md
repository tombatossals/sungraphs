# AGENTS.md

Solar monitoring system: Python collectors poll APSystems / GoodWe SEMS / Victron devices, write daily JSON files into `data/`, a React (Vite + TypeScript) dashboard renders those JSONs as static files, and a Telegram bot (`bot.py`) reports on them. No CI; README and code comments are in Spanish. There is no `pyproject.toml` and no Python lint/format config.

## Commands

- Use the venv for everything Python: `.venv/bin/python` (Python 3.13, deps in `requirements.txt`).
- Python tests: `.venv/bin/python -m unittest discover -s tests` (unittest; test files inject the repo root into `sys.path` themselves, so no `PYTHONPATH` needed).
- Frontend (from `frontend/`): `npm run dev`, `npm run build` (= `tsc -b && vite build`), `npm run lint`, `npm test` (vitest, jsdom; config lives in `vite.config.ts`, tests in `src/__tests__`).
- Daily regeneration, always run both in order for the same date:
  `.venv/bin/python generate_history.py YYYY-MM-DD && .venv/bin/python generate_daily_data.py YYYY-MM-DD`
- VRM backfill for Victron gaps: `.venv/bin/python collect.py --recover-victron-day YYYY-MM-DD`.

## Data model

- `data/<device>-YYYY-MM-DD.json` per device per day; Victron and `shelly_em` samples are `<device>-<sample>-YYYY-MM-DD.json`. Values live under `intervals` keyed by 10-minute slot (stringified unix epoch, 600s). GoodWe files use `totals.p1/p2` (Wh), APSystems a different shape.
- `generate_daily_data.py` merges all per-day files into the bundle `data/daily-YYYY-MM-DD.json` with shape `{date, generated_at, metadata, skipped_files, devices}` — this bundle is what the frontend and `bot.py` consume. It raises if no daily files exist for the date.
- `data/history.json` holds per-day totals; only "production" device types count: `apsystems`, `goodwe_sems` (`PRODUCTION_DEVICE_TYPES` in `generate_history.py`).
- `data/metadata.json` (written by `collect.py` from `config.toml`) drives device ordering and labels everywhere — keep it in sync with `config.toml` when adding devices/samples.
- `data/victron.json` is the latest snapshot of all Victron samples.

## Gotchas

- `bot.py` imports `python-telegram-bot`, which is **not** in `requirements.txt` — install it manually before running/testing the bot. Token comes from `TELEGRAM_BOT_TOKEN` env or a `[telegram]` section in `config.toml`; without it the bot exits.
- `config.toml` is committed and contains live credentials (GoodWe account/password, LAN IPs). Never log or print these values.
- Collectors need LAN access to devices at `192.168.x.x`; running `collect.py` off-network just times out — don't treat that as a code failure.
- `collect.sh` (cron/launchd, every 10 min) and `generate_history.sh` run the scripts then `git add -A`, commit (`data: collect ...`), and push. Committing generated data JSONs is the normal workflow here, not noise.
- `generate_history.sh` uses `date -d` (GNU coreutils); it will fail on macOS's default `date`. `collect.sh` does not have this issue.
