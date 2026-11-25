# Snapshots de la cámara de las placas

## Intención
Cada ejecución de `collect.sh` (cada 10 min) guarda una foto de la cámara Foscam que enfoca a las placas. La web muestra una miniatura de la última foto del día seleccionado y un visor timelapse para ver cómo ha evolucionado el día (luz, sombras, nubes), enlazado con la curva de producción.

## Objetivos / no-objetivos / anti-objetivos
- Objetivo: captura automática, miniatura, visor con deslizador + reproducción y sincronización con la gráfica de producción.
- No-objetivo: vídeo en directo, control PTZ, archivo de fotos a largo plazo.
- Anti-objetivo: fotos en git (bloat del repo y privacidad: el repo está en GitHub); que un fallo de la cámara rompa la recogida de datos.

## Restricciones
- Las fotos viven en `data/camera/YYYY-MM-DD/HHMM.jpg` + `data/camera/YYYY-MM-DD/index.json`; `data/camera/` va en `.gitignore`.
- Retención: se borran los días de más de 30 días.
- Sin dependencias nuevas de Python: descarga con `requests`; redimensionado a ~960 px con `/usr/bin/sips` (macOS) si está disponible, si no se guarda el original.
- La URL incluye credenciales: nunca se registra en logs.

## Enfoques considerados
- A. URL de snapshot HTTP: simple, depende de la cámara.
- B. RTSP + ffmpeg: universal, más piezas.
- C. Ambas según config. Elegido inicialmente; tras recibir la URL (Foscam `snapPicture2`) basta con A, así que se implementa solo `snapshot_url`. RTSP queda fuera (YAGNI).

## Diseño
- `config.toml` → `[camera] snapshot_url, latitude, longitude, retention_days=30`.
- `snapshot.py`: si el sol está por encima de −6° (crepúsculo civil, cálculo NOAA sin dependencias) descarga la foto, la guarda redimensionada y actualiza `index.json` (`{date, images:[{time:"HH:MM", ts, file}]}`); limpia días antiguos. Errores → mensaje en stderr y código 0.
- `collect.sh`: `snapshot.py ... || true` tras `collect.py`.
- Frontend: hook `useCameraIndex(date)`; componente `CameraTimelapse` con miniatura (última foto) que abre un visor con deslizador, ▶/⏸, hora y potencia en ese momento; al mover el deslizador se marca la hora en `EnergyFlowChart` (línea vertical). Si no hay `index.json` para el día, no se muestra nada.

## Corrección respecto a lo hablado
El proyecto no calculaba la posición del sol; se añade un cálculo propio en `snapshot.py`.

## Decisiones dejadas al constructor
Estilo exacto del visor, velocidad del timelapse (~4 fps), precarga de imágenes.
