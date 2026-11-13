# Contrato API / WebSocket — nmap-custom

- **Versión:** 1.0 (baseline)
- **Fecha:** 2026-11-11
- **Decisiones relacionadas:** DEC-006 (contrato de progreso y tiempo real), DEC-007 (semántica de ejecución/métricas), DEC-008 (ejecución de schedules)
- **Implementación backend:** `backend/app/api/scans.py`, `backend/app/api/websocket.py`, `backend/app/schemas/scan.py`
- **Tipos frontend:** `frontend/src/types/index.ts`, `frontend/src/services/websocket.ts`
- **Pruebas de contrato:** `backend/tests/api/test_scan_contract.py`, `backend/tests/api/test_scans_lifecycle.py`

Este documento es la fuente de verdad del contrato entre backend y frontend. Cualquier cambio de campos, estados o mensajes debe actualizar este archivo, los schemas/tipos y las pruebas de contrato en el mismo cambio.

---

## 1. Enumeraciones compartidas

### `ScanType`
`tcp_connect` | `tcp_syn` | `udp` | `comprehensive`

### `ScanStatus`
`pending` | `running` | `completed` | `failed` | `cancelled`

Estados terminales: **`completed`**, **`failed`**, **`cancelled`**. Un scan terminal no vuelve a progresar y el WebSocket se cierra tras emitir su estado final.

### `PortState`
`open` | `closed` | `filtered` | `unknown`

---

## 2. Entidades

### 2.1 `ScanSummary` — listados (`GET /api/scans`)

| Campo | Tipo | Notas |
|---|---|---|
| `id` | int | |
| `name` | string \| null | |
| `target` | string | IP, CIDR o hostname |
| `scan_type` | `ScanType` | |
| `status` | `ScanStatus` | |
| `port_range` | string \| null | p. ej. `1-1000,8080` |
| `service_detection` | bool | |
| `os_detection` | bool | |
| `aggressive` | bool | |
| `progress` | int | 0–100 |
| `current_host` | string \| null | |
| `hosts_total` | int | |
| `hosts_scanned` | int | |
| `created_at` | datetime (ISO 8601) | |
| `started_at` | datetime \| null | |
| `completed_at` | datetime \| null | |
| `total_hosts_up` | int | |
| `total_ports_found` | int | |
| `error_message` | string \| null | motivo de fallo/cancelación |
| `task_id` | string \| null | id de la tarea Celery |

**No incluye `results`** (payload pesado). Schema: `ScanSummaryResponse`.

### 2.2 `ScanDetail` — detalle (`GET /api/scans/{id}`, `PATCH`)

`ScanSummary` **+**

| Campo | Tipo |
|---|---|
| `results` | `ScanResult[]` |

Schema: `ScanResponse` (hereda de `ScanSummaryResponse`).

### 2.3 `ScanResult`

`id`, `scan_id`, `ip_address`, `hostname?`, `mac_address?`, `is_up`, `os_name?`, `os_accuracy?`, `os_details?`, `latency?`, `scanned_at`, `ports: PortInfo[]`

### 2.4 `PortInfo`

`port_number`, `protocol` (`tcp`/`udp`), `state` (`PortState`), `service_name?`, `service_product?`, `service_version?`, `service_extra_info?`, `banner?`

---

## 3. Endpoints REST

Base: `/api/scans`

| Método | Ruta | Cuerpo | Respuesta | Errores |
|---|---|---|---|---|
| `POST` | `/api/scans` | `ScanCreate` | `201` + `ScanDetail` | `422` validación |
| `GET` | `/api/scans` | — (`skip`, `limit`, `status_filter`) | `200` + `ScanSummary[]` | — |
| `GET` | `/api/scans/{id}` | — | `200` + `ScanDetail` | `404` |
| `PATCH` | `/api/scans/{id}` | `{ name?, status? }` | `200` + `ScanDetail` | `404`, `422` |
| `DELETE` | `/api/scans/{id}` | — | `204` sin cuerpo | `404` |
| `POST` | `/api/scans/{id}/export` | `{ format: "json" \| "csv" \| "xml" }` | `200` archivo | `404`, `422` |

### 3.1 `ScanCreate`

```json
{
  "name": "opcional",
  "target": "192.168.1.0/24",
  "scan_type": "tcp_connect",
  "port_range": "1-1000",
  "service_detection": true,
  "os_detection": false,
  "aggressive": false
}
```

`target` se normaliza con `strip()` y no puede quedar vacío (`422`). `scan_type` por defecto `tcp_connect`.

**Validación estricta (PLAN-031):**

- `target` acepta IPv4, IPv6, CIDR (`10.0.0.0/8`), rango IPv4 (`192.168.1.10-192.168.1.20`) y hostnames sintácticamente válidos. No se resuelven DNS durante la validación.
- `port_range` acepta listas y rangos separados por comas (`22,80,443`, `1-1000`, `22,100-200`); se normaliza sin espacios. Cada puerto debe estar entre 1 y 65535 y el fin no puede preceder al inicio.
- `scan_config` de schedules aplica las mismas validaciones sobre `target`/`port_range` y valida `scan_type` contra el enum; configuración inválida → `422`.
- **Límites de recursos:** `MAX_HOSTS_PER_SCAN` (default `1024`) y `MAX_PORTS_PER_SCAN` (default `65535`) se configuran por entorno. Un CIDR/rango que supere el máximo de hosts, o una lista que supere el máximo de puertos, se rechaza con `422`; no se trunca silenciosamente.
- **CORS:** `CORS_ORIGINS` debe listar orígenes explícitos (`http://localhost:5173`); el wildcard `*` y una lista vacía fallan al arrancar la configuración.

### 3.2 Ciclo de vida y cancelación

- `POST` crea el scan en `pending`, encola la tarea y persiste `task_id`.
- `PATCH` con `status: "cancelled"` sobre un scan `pending`/`running`:
  - revoca la tarea Celery si existe `task_id`;
  - persiste `status = cancelled`, `completed_at` (si no existía) y `error_message = "Scan cancelled by user"` (si no existía).
- `PATCH` con otros estados solo persiste el valor (no hay máquina de estados estricta en el baseline).
- `DELETE` revoca la tarea si el scan está `pending`/`running` y elimina el scan junto con sus resultados (`cascade`).

### 3.3 Exportación

| Formato | `Content-Type` | Contenido |
|---|---|---|
| `json` | `application/json` | `{ scan: {...}, results: [...] }` (`ports` con `port` en vez de `port_number`) |
| `csv` | `text/csv` | Cabecera `IP Address,Hostname,Port,Protocol,State,Service,Version` |
| `xml` | `application/xml` | Estilo nmap: `<nmaprun>` / `<host>` / `<port protocol="tcp" portid="80">` |

Formatos no soportados → `422` (validación del schema `ExportRequest`).

### 3.4 Errores y resiliencia (PLAN-032)

Formato estándar de FastAPI:

```json
{ "detail": "Scan 42 not found" }
```

Política de errores:

- **`4xx`** conservan detalle accionable (`404` recurso inexistente, `422` validación con campo).
- **`500` no controlado** → `{ "detail": "Internal server error" }`; el traceback y los detalles internos se registran en el log (`Unhandled error on <METHOD> <path>`) y nunca se devuelven al cliente.
- **Timeout de escaneo:** la tarea se aborta tras `DEFAULT_SCAN_TIMEOUT` (default `300` s), el scan pasa a `failed` con mensaje `Scan exceeded the configured timeout of Ns` y se emite `scan.timeout`.
- **Fallos por host:** un error al escanear un host no aborta el resto; se omite, se cuenta en `hosts_failed` y el scan termina con los hosts restantes.
- **Idempotencia:** una entrega duplicada de la tarea sobre un scan en estado terminal (`completed`/`failed`/`cancelled`) no se re-ejecuta; responde `{"status": "skipped"}` y emite `scan.skipped`.
- **Mensajes persistidos:** se truncan a 500 caracteres y los errores de base de datos se sustituyen por `Scan failed due to a database error`.
- **Resolución DNS inversa:** `RESOLVE_HOSTNAMES` (default `true`) permite desactivarla en entornos sin DNS o de baja latencia; los fallos de resolución se ignoran.

### 3.5 Schedules — `/api/schedules` (DEC-008)

| Método | Ruta | Cuerpo | Respuesta | Errores |
|---|---|---|---|---|
| `POST` | `/api/schedules` | `ScheduleCreate` | `201` + `Schedule` | `422` (cron inválido) |
| `GET` | `/api/schedules` | — (`skip`, `limit`) | `200` + `Schedule[]` | — |
| `GET` | `/api/schedules/{id}` | — | `200` + `Schedule` | `404` |
| `PATCH` | `/api/schedules/{id}` | `ScheduleUpdate` | `200` + `Schedule` | `404`, `422` |
| `DELETE` | `/api/schedules/{id}` | — | `204` sin cuerpo | `404` |

- `cron_expression` se valida con `croniter` (5 campos estándar); expresión inválida → `422`.
- `next_run_at` es calculado por el backend: se define al crear un schedule `enabled: true`, se recalcula si cambia `cron_expression` o se reactiva, y se limpia (`null`) al deshabilitarlo.
- El despacho es asíncrono (Celery Beat cada 60 s + `dispatch_due_schedules`): el `POST` **no** implica ejecución inmediata. Un schedule vencido crea un `Scan` `pending` usando `scan_config` y encola `perform_scan_task`.
- `scan_config` requiere `target`; `scan_type` por defecto `tcp_connect`. Configuración inválida avanza `next_run_at`, cuenta `failed_runs` y no bloquea al resto.
- Los contadores `total_runs`/`successful_runs`/`failed_runs` se actualizan en el despacho.

### 3.6 Operación — `/api/health` y `/api/metrics` (PLAN-040)

Endpoints de solo lectura para contenedores y smoke checks; no exponen datos de escaneo.

| Método | Ruta | Respuesta | Errores |
|---|---|---|---|
| `GET` | `/api/health` | `200` + `{ "status": "healthy", "database": "connected" }` | `503` + `{ "status": "degraded", "database": "unavailable" }` |
| `GET` | `/api/metrics` | `200` + agregados (ver abajo) | — |

- `health` ejecuta `SELECT 1` contra la base; un fallo de conexión devuelve `503` para que el orquestador marque el contenedor como no saludable.
- `metrics` agrega estado de scans sin devolver `results`:

```json
{
  "scans": {
    "total": 5,
    "by_status": { "completed": 2, "failed": 1, "pending": 1, "running": 1 },
    "active": 2
  },
  "hosts_up_total": 6,
  "ports_found_total": 17
}
```

`active` = `pending + running`; `by_status` omite estados sin scans y los totales usan `coalesce` (`0` con base vacía).

### 3.7 Logging estructurado

Los logs del backend se emiten como **una línea JSON** (`app/core/logging_utils.py`) con `timestamp`, `level`, `logger`, `message` y, si aplican, `scan_id`, `task_id`, `event`, `status`, `duration_ms`, `hosts_found`, `ports_found` y `exception` (traceback). Las tareas usan `get_scan_logger(scan_id, task_id=...)` con eventos `scan.started`, `scan.completed`, `scan.failed`, `scan.not_found` y `scan.progress_error`.

---

## 4. WebSocket — `/ws/scan/{scan_id}`

### 4.1 Conexión

- Al aceptar, el backend envía un mensaje `status` con el snapshot actual.
- Después hace *polling* de la base de datos (fuente de verdad) y envía `update` cuando el snapshot cambia.
- Heartbeat: el cliente envía el texto `ping`; el servidor responde el texto `pong` (no es JSON).
- Si el scan no existe: mensaje `error` y cierre inmediato.
- Si el scan ya está en estado terminal: mensaje `status` y cierre inmediato (sin `update`).
- Cuando el scan alcanza un estado terminal durante el polling: `update` final + cierre.

### 4.2 `status` / `update`

```json
{
  "type": "status",
  "scan_id": 42,
  "status": "running",
  "progress": 40,
  "current_host": "192.168.1.10",
  "hosts_scanned": 2,
  "hosts_total": 5,
  "ports_found": 7,
  "error_message": null
}
```

`type` es `status` (mensaje inicial) o `update` (cambio detectado). El resto de campos es el **snapshot** persistido: `status`, `progress`, `current_host`, `hosts_scanned`, `hosts_total`, `ports_found` (= `total_ports_found`), `error_message`. Los campos anulables pueden ser `null`.

### 4.3 `error`

```json
{ "type": "error", "scan_id": 999, "message": "Scan 999 not found" }
```

### 4.4 Reglas de cliente

- Ignorar mensajes de texto `pong` (no intentar `JSON.parse`).
- No reconectar cuando el cierre es intencional (`disconnect()`) ni tras un estado terminal.
- Aceptar `null` en campos opcionales y tolerar campos adicionales.
- Los tipos TypeScript equivalentes son `ScanSnapshotMessage`, `ScanErrorMessage` y `ScanWSMessage` en `frontend/src/types/index.ts`.

### 4.5 Constructores de payload (backend)

`backend/app/api/websocket.py` expone funciones puras para testear el contrato sin sockets:

- `scan_snapshot(scan) -> dict`
- `build_status_message(scan) -> dict`
- `build_update_message(scan) -> dict`
- `build_error_message(scan_id, message) -> dict`
- `TERMINAL_STATUSES = ("completed", "failed", "cancelled")`

---

## 5. Mapa schema ↔ tipo frontend

| Backend (`app/schemas/scan.py`) | Frontend (`src/types/index.ts`) |
|---|---|
| `ScanSummaryResponse` | `ScanSummary` |
| `ScanResponse` | `Scan` (con `results?`) |
| `ScanResultResponse` | `ScanResult` |
| `PortInfo` | `PortInfo` |
| `ScanCreate` | `ScanCreateRequest` |
| `ScanProgress` (legacy) | reemplazado por `ScanSnapshotMessage` |

---

## 6. Verificación del contrato

```powershell
cd backend
$env:PYTHONPATH='.'
$env:DATABASE_URL='sqlite:///:memory:'
python -m pytest tests/api tests/core -q
```

Cobertura de contrato actual:

- `TestScanContract`: listado resumen sin `results`, detalle con `results/ports`, filtros/paginación, validación de `POST`/`PATCH`, export `json`/`csv`/`xml` y errores `404`/`422`.
- `TestSchemaContract`: separación resumen/detalle, defaults y validaciones de `ScanCreate`, normalización/rechazo de `ExportRequest`.
- `TestWebSocketMessageBuilders`: campos exactos de `status`, `update` y `error`; estados terminales.
- `TestWebSocketContract`: scan inexistente → `error`; scan terminal → `status` + cierre.
- `TestScanLifecycle`: creación/encolado, cancelación por `PATCH`, `DELETE` con revocación, `404`.
- `TestScheduleContract`: `next_run_at` en creación/edición/deshabilitado, cron inválido `422`, CRUD y `404`.
- `test_scheduler.py`: cálculo de `next_run_at`, mapeo `scan_config`→`Scan`, despacho idempotente, fallos de enqueue/config y cron inválido.
- `test_dispatch_task.py`: entrada Celery de despacho (conteo y cierre de sesión, incluso con error).
- `test_validation.py` / `test_input_validation.py`: targets y puertos válidos/inválidos, normalización, límites de hosts/puertos y rechazo `422` en scans y `scan_config` de schedules.
- `test_config.py`: CORS explícito (rechazo de `*`/lista vacía), límites positivos y detección del `SECRET_KEY` placeholder.
- `test_system.py`: `/api/health` saludable y `503` degradado con fallo de DB simulado; `/api/metrics` con conteos por estado, activos y totales (incluida base vacía).
- `test_logging_utils.py`: campos de correlación en JSON, traceback, tolerancia a `exc_info=True` sin excepción activa, inyección/override de `scan_id`/`task_id` y configuración idempotente por logger.
- `test_resilience.py`: idempotencia sobre scans terminales, timeout con mensaje no sensible, truncado de errores, persistencia de resultados y aislamiento de fallos por host (`hosts_failed`).
- `test_error_handling.py`: `500` genérico sin filtrar internos, `404` con detalle y `422` con errores de campo.

Pendiente: validación E2E de WS en un entorno de red autorizado (DEC-004).
