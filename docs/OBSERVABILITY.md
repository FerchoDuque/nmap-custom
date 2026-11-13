# Observabilidad (PLAN-040)

Guía de las señales operativas del backend: logs estructurados, health y
métricas básicas. No requiere servicios externos ni añade dependencias.

## Logs estructurados

Cada registro se emite como **una línea JSON** en `stdout` (formato en
`backend/app/core/logging_utils.py`, configurado al arrancar en `main.py`).

```json
{"timestamp":"2026-11-13T18:22:41.512+00:00","level":"INFO","logger":"app.scans","message":"Scan completed","scan_id":42,"task_id":"d1f0-...","event":"scan.completed","status":"completed","hosts_found":6,"ports_found":17}
```

| Campo | Origen | Notas |
|---|---|---|
| `timestamp` | `record.created` | ISO 8601 en UTC |
| `level`, `logger`, `message` | estándar | `message` ya interpolado |
| `scan_id`, `task_id` | `ScanLoggerAdapter` | correlación scan ↔ tarea Celery |
| `event` | `extra` | `scan.started`, `scan.completed`, `scan.failed`, `scan.not_found`, `scan.progress_error`, `scan.timeout`, `scan.skipped`, `scan.persist_error` |
| `status`, `duration_ms`, `hosts_found`, `ports_found` | `extra` | solo si se informan |
| `exception` | `exc_info` | traceback completo |

Uso en tareas:

```python
from app.core.logging_utils import get_scan_logger

scan_log = get_scan_logger(scan_id, task_id=task_id)
scan_log.info("Scan started", extra={"event": "scan.started"})
```

`get_scan_logger` acepta un `logger` opcional (por defecto `app.scans`) para
tests o sinks alternativos. `configure_logging(...)` es idempotente por logger:
no duplica handlers si se invoca varias veces.

Filtrar un scan en local:

```bash
docker-compose logs -f backend | grep '"scan_id":42'
```

## Health

`GET /api/health` valida conectividad real con la base (`SELECT 1`):

- `200` → `{"status":"healthy","database":"connected"}`
- `503` → `{"status":"degraded","database":"unavailable"}` (el orquestador debe
  marcar el contenedor como no saludable)

El `HEALTHCHECK` del `backend/Dockerfile` usa solo la librería estándar
(`urllib.request`), así que no depende de paquetes extra. Cualquier respuesta
`5xx` hace que `urlopen` lance excepción y el check falle.

## Métricas

`GET /api/metrics` devuelve agregados de solo lectura (sin `results`):

```json
{
  "scans": {
    "total": 5,
    "by_status": {"completed": 2, "failed": 1, "pending": 1, "running": 1},
    "active": 2
  },
  "hosts_up_total": 6,
  "ports_found_total": 17
}
```

- `active` = `pending + running`.
- `by_status` omite estados sin scans.
- Los totales usan `coalesce` para devolver `0` con la base vacía.

## Smoke checks

```powershell
curl.exe -s http://localhost:8000/api/health
curl.exe -s http://localhost:8000/api/metrics
```

## Pruebas

```powershell
cd backend
$env:PYTHONPATH='.'
$env:DATABASE_URL='sqlite:///:memory:'
python -m pytest tests/core/test_logging_utils.py tests/api/test_system.py -q
```

Cubren campos de correlación, traceback, `exc_info=True` sin excepción activa,
override de `scan_id`, idempotencia de handlers, health degradado con DB
simulada y métricas con/sin datos. Todo determinista y sin red (DEC-004/010).

## Limitaciones

- No hay exportador Prometheus/OpenTelemetry; si se necesita, se añadirá como
  decisión aparte manteniendo el endpoint actual como contrato estable.
- El nivel de log es fijo en `INFO` al arrancar; ajustarlo por entorno queda
  para una iteración de configuración.
- Las métricas se calculan por consulta; con volúmenes grandes conviene caché o
  agregados materializados.
