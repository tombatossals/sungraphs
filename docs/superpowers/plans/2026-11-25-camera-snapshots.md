# Snapshots de la cámara — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capturar una foto de la cámara en cada `collect.sh` y mostrar en la web una miniatura + visor timelapse sincronizado con la gráfica de producción.

**Architecture:** `snapshot.py` (independiente de `collect.py`) descarga la foto si es de día, la guarda redimensionada en `data/camera/<fecha>/HHMM.jpg` y mantiene `index.json`. El frontend lee ese índice como fichero estático; `CameraTimelapse` gestiona el visor y comunica la hora seleccionada a `EnergyFlowChart`, que dibuja una línea vertical.

**Tech Stack:** Python 3.13 + requests + `/usr/bin/sips`; React 19 + TS + chart.js (plugin inline) + vitest/testing-library.

**Spec:** `docs/superpowers/specs/2026-11-25-camera-snapshots-design.md`

## Global Constraints
- Fotos en `data/camera/YYYY-MM-DD/HHMM.jpg`, índice `data/camera/YYYY-MM-DD/index.json` = `{"date": "YYYY-MM-DD", "images": [{"time": "HH:MM", "ts": <epoch int>, "file": "HHMM.jpg"}]}` ordenado por `ts`.
- `data/camera/` en `.gitignore`. Retención por defecto 30 días.
- Sin dependencias Python nuevas. Nunca imprimir `snapshot_url` (lleva usuario y contraseña).
- Captura solo si elevación solar > −6°.
- Fallo de cámara → mensaje en stderr sin la URL, exit 0.
- Textos de UI en español.

## Review Focus
- Cámara apagada / timeout → `collect.sh` sigue y hace commit (test: `test_capture_failure_returns_false_without_url_in_output`).
- Día sin `index.json` (fechas pasadas, 404) → el componente no renderiza nada (test: `renders nothing when index missing`).
- Dos ejecuciones en el mismo minuto → no duplica la entrada del índice (test: `test_update_index_replaces_same_time`).
- `index.json` corrupto o a medio escribir → se reescribe desde cero; escritura atómica con fichero temporal + `os.replace` (test: `test_update_index_recovers_from_corrupt_file`).
- Hora de la foto sin intervalo exacto en la gráfica → la marca va al label más cercano (test: `nearestLabelIndex`).

---

### Task 1: Captura en backend (`snapshot.py`)

**Files:**
- Create: `snapshot.py`, `tests/test_snapshot.py`
- Modify: `config.toml` (nueva sección `[camera]`), `.gitignore`, `collect.sh`

**Interfaces:**
- Produces: `data/camera/<fecha>/index.json` con el formato de Global Constraints.
- `solar_elevation(when: datetime, lat: float, lon: float) -> float` (grados; `when` con tz)
- `update_index(day_dir: Path, date: str, time_hhmm: str, ts: int, filename: str) -> dict`
- `prune_old_days(camera_dir: Path, today: date, retention_days: int) -> list[str]` (devuelve fechas borradas)
- `capture(url: str, dest: Path, timeout: float = 15) -> bool`
- `main(argv=None) -> int`; flag `--force` ignora la comprobación de sol.

- [ ] **Step 1: tests** en `tests/test_snapshot.py` (unittest, inyecta la raíz en `sys.path` como los demás):
  - `test_solar_elevation_noon_positive`: 2026-06-21 12:00 UTC, lat 40.0, lon 0.0 → `> 60`.
  - `test_solar_elevation_midnight_negative`: 2026-06-21 00:00 UTC mismo sitio → `< -6`.
  - `test_update_index_appends_sorted`: insertar 10:20 y luego 10:10 → `[t["time"] for t in images] == ["10:10","10:20"]`.
  - `test_update_index_replaces_same_time`: dos veces `"10:10"` → `len(images) == 1`.
  - `test_update_index_recovers_from_corrupt_file`: `index.json` con `"{"` → resultado válido con 1 imagen.
  - `test_prune_old_days`: dirs `2026-10-01`, `2026-11-20`, `notadate` con today 2026-11-25, retention 30 → borra solo `2026-10-01`; `notadate` intacto.
  - `test_capture_failure_returns_false_without_url_in_output`: `requests.get` parcheado lanza `ConnectionError` con la URL en el mensaje; `capture` → `False`, stderr capturado no contiene `"pwd="`.
  - `test_capture_rejects_non_jpeg`: respuesta 200 con cuerpo `b"<html>"` → `False`, sin fichero creado.
- [ ] **Step 2:** `.venv/bin/python -m unittest tests.test_snapshot` → FAIL (módulo no existe).
- [ ] **Step 3: implementar `snapshot.py`.** Config de `config.toml` `[camera]`: `snapshot_url`, `latitude`, `longitude`, `retention_days` (30). Elevación con la aproximación NOAA (declinación + ecuación del tiempo + ángulo horario). `capture`: GET, exigir status 200 y que el cuerpo empiece por `b"\xff\xd8"`; escribir en temporal y, si existe `/usr/bin/sips`, `sips -Z 960`; luego `os.replace`. Mensajes de error: solo el tipo de excepción, nunca `str(exc)`. Hora local del sistema para `HH:MM`/fecha. Sin sección `[camera]` → mensaje y exit 0.
- [ ] **Step 4:** tests → PASS; suite completa `.venv/bin/python -m unittest discover -s tests` → PASS.
- [ ] **Step 5:** añadir a `config.toml` `[camera]` con la URL dada por el usuario, `latitude`/`longitude` de la instalación, `retention_days = 30`; `data/camera/` a `.gitignore`; en `collect.sh` tras `collect.py`: `"$BASE_DIR/.venv/bin/python" snapshot.py || true`.
- [ ] **Step 6:** prueba real `.venv/bin/python snapshot.py --force` → crea jpg + index; `git status` no muestra `data/camera`.
- [ ] **Step 7: commit** `snapshot.py tests/test_snapshot.py config.toml .gitignore collect.sh`.

### Task 2: Visor timelapse (frontend)

**Files:**
- Create: `frontend/src/camera.ts`, `frontend/src/components/CameraTimelapse.tsx`, `frontend/src/__tests__/camera.test.ts`, `frontend/src/__tests__/CameraTimelapse.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `index.json` de Task 1.
- `export interface CameraImage { time: string; ts: number; file: string }`
- `export interface CameraIndex { date: string; images: CameraImage[] }`
- `export function cameraImageUrl(date: string, file: string): string` → `/data/camera/${date}/${file}`
- `export function useCameraIndex(date: string): CameraIndex | null` (404/error → `null`; refetch cada 5 min como `useSolarData`)
- `CameraTimelapse({ date: string; onTimeChange: (time: string | null) => void })`

- [ ] **Step 1: tests.** `camera.test.ts`: `cameraImageUrl("2026-11-25","1210.jpg") === "/data/camera/2026-11-25/1210.jpg"`. `CameraTimelapse.test.tsx` (fetch mockeado): `renders nothing when index missing` (404 → contenedor vacío); con 3 imágenes muestra miniatura con `src` de la última y su hora; al pulsarla aparece un `input[type=range]` con `max=2`; cambiar el slider a 0 → `onTimeChange("<hora 0>")` y la imagen grande cambia de `src`; cerrar → `onTimeChange(null)`.
- [ ] **Step 2:** `npm test` → FAIL.
- [ ] **Step 3: implementar.** Miniatura (última foto, hora encima). Visor en el mismo panel (no modal a pantalla completa): imagen grande, slider, botón ▶/⏸ a ~4 fps que vuelve al principio al llegar al final, hora actual, botón cerrar. Precargar todas las imágenes al abrir (`new Image()`). Estilo con las variables CSS existentes (`--panel`, `--border`, `--text-soft`).
- [ ] **Step 4:** en `App.tsx`, estado `cameraTime` y `<CameraTimelapse date={date} onTimeChange={setCameraTime} />` entre `InverterStats` y `VictronStats`. Si `date` es `""` usar la fecha que resuelve `useSolarData` (revisar qué expone; si no expone la fecha efectiva, usar la del día actual local).
- [ ] **Step 5:** `npm test && npm run lint && npm run build` → PASS.
- [ ] **Step 6: commit.**

### Task 3: Marca de hora en la gráfica de producción

**Files:**
- Modify: `frontend/src/components/EnergyFlowChart.tsx`, `frontend/src/App.tsx`
- Create: `frontend/src/__tests__/nearestLabelIndex.test.ts`

**Interfaces:**
- Consumes: `cameraTime: string | null` de Task 2.
- `export function nearestLabelIndex(labels: string[], time: string): number` (−1 si no hay labels válidos) en `EnergyFlowChart.tsx`.
- `EnergyFlowChart` recibe prop opcional `markerTime?: string | null`; solo el bloque "Producción" dibuja la marca.

- [ ] **Step 1: tests** `nearestLabelIndex(["10:00","10:10","10:20"], "10:14") === 1`; `"10:16"` → 2; `"23:00"` → 2; `[]` → −1; labels con `""` se ignoran.
- [ ] **Step 2:** `npm test` → FAIL.
- [ ] **Step 3: implementar** `nearestLabelIndex` y un plugin chart.js inline (`afterDatasetsDraw`) que dibuja una línea vertical discontinua en `scales.x.getPixelForValue(index)` con el color `--chart-text`; pasar `markerTime` desde `App`.
- [ ] **Step 4:** `npm test && npm run lint && npm run build` → PASS; comprobar en `npm run dev` que mover el slider mueve la línea.
- [ ] **Step 5: commit.**
