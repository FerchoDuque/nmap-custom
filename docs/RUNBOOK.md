# Runbook de operación (PLAN-042)

Guía para operar, diagnosticar y recuperar **nmap-custom** en local o en un
entorno autorizado. Complementa [`CONTRACT.md`](CONTRACT.md),
[`OBSERVABILITY.md`](OBSERVABILITY.md), [`DOCKER.md`](DOCKER.md) y
[`CI.md`](CI.md).

> Alcance: solo redes propias o con autorización explícita (DEC-004). Un
> operador no debe lanzar escaneos contra objetivos de terceros.

## 1. Servicios y puertos

| Servicio | Contenedor | Puerto host | Notas |
|---|---|---|---|
| `db` | `scanner-db` | — (red interna 5432) | PostgreSQL 15, healthcheck `pg_isready` |
| `redis` | `scanner-redis` | — (red interna 6379) | Broker/result backend de Celery |
| `backend` | `scanner-backend` | `8001` → `8000` | FastAPI + `NET_RAW`/`NET_ADMIN` |
| `celery` | `scanner-celery` | — | Worker `--pool=solo`, mismas capacidades |
| `beat` | `scanner-beat` | — | Despachador de schedules cada 60 s, **sin** capacidades |
| `frontend` | `scanner-frontend` | `80` | Nginx + build de Vite |

URLs esperadas: frontend `http://localhost/`, API `http://localhost:8001/api`,
docs `http://localhost:8001/api/docs`.

## 2. Ciclo de vida

```bash
make prod          # build + up (producción)
make dev           # build + up con hot reload
make ps            # estado de contenedores
make logs          # logs de todos los servicios
make logs-backend  # solo API
make logs-celery   # solo worker
make down          # parar
```

Reinicio selectivo: `make restart-backend` / `make restart-celery`.

## 3. Chequeo de salud

```bash
curl -s http://localhost:8001/api/health   # 200 healthy | 503 degraded
curl -s http://localhost:8001/api/metrics  # agregados de scans
docker-compose ps
```

- `503 degraded` ⇒ la API no alcanza PostgreSQL; revisar `make logs-backend` y
  `docker-compose ps db`.
- El `HEALTHCHECK` del contenedor usa `urllib` (sin `requests`); si el
  healthcheck falla, el backend no está sirviendo o no ve la base.

## 4. Diagnóstico por síntoma

### 4.1 API responde `500` o no responde

1. `curl -i http://localhost:8001/api/health`.
2. `make logs-backend` y buscar `"level": "ERROR"`.
3. Los errores no controlados se registran como `Unhandled error on <METHOD>
   <path>` con traceback; el cliente solo recibe
   `{"detail": "Internal server error"}`.
4. Si la base está caída: `docker-compose restart db` y esperar `pg_isready`.

### 4.2 Scans quedan en `pending`

1. `docker-compose ps` ⇒ `celery` y `redis` deben estar `Up/healthy`.
2. `docker-compose logs --tail=100 celery` buscando errores de conexión al
   broker.
3. `docker-compose exec celery celery -A app.celery_app:celery_app inspect active` (el
   worker usa `--pool=solo`).
4. Reiniciar worker: `make restart-celery`.

### 4.3 Scan en `failed`

- **Timeout:** `error_message` contiene `Scan exceeded the configured timeout
  of Ns`. Reducir alcance (`MAX_HOSTS_PER_SCAN`, `MAX_PORTS_PER_SCAN`) o subir
  `DEFAULT_SCAN_TIMEOUT` de forma consciente.
- **Hosts omitidos:** el resultado puede incluir `hosts_failed > 0`; repetir el
  escaneo del host o revisar conectividad.
- **DNS inverso lento:** `RESOLVE_HOSTNAMES=false` evita esperas de resolución.
- **Permisos:** `tcp_syn`, `udp` y `os_detection` requieren capacidades; usar
  `tcp_connect` para diagnóstico sin privilegios.

### 4.4 Un scan no se puede cancelar

`PATCH /api/scans/{id}` con `{"status": "cancelled"}` revoca la tarea Celery y
marca el scan como `cancelled`. Si el proceso ya terminó, el estado terminal no
se reejecuta (idempotencia).

### 4.5 Schedules no disparan

1. `docker-compose ps beat` debe estar `Up`.
2. `docker-compose logs --tail=100 beat` (tarea `dispatch_due_schedules`).
3. En la UI `/schedules`, revisar `next_run_at` y `enabled`.
4. Cron inválido ya se rechaza con `422`; si `failed_runs` crece, revisar
   `scan_config.target`/`port_range`.
5. El despacho es cada 60 s: un schedule recién creado puede tardar hasta un
   minuto en ejecutarse.

### 4.6 Logs y correlación

```bash
make logs-backend | grep '"scan_id":42'
make logs-celery  | grep '"task_id":"<uuid>"'
```

Eventos útiles: `scan.started`, `scan.completed`, `scan.failed`, `scan.timeout`,
`scan.skipped`, `scan.not_found`, `scan.progress_error`, `scan.persist_error`.

### 4.7 Base de datos y migraciones

```bash
docker compose exec backend python -m app.core.db_migrations   # upgrade a head
docker compose exec backend alembic current                    # revisión aplicada
make shell-db                                                  # psql
```

El arranque del contenedor `backend` ya aplica las migraciones. Una base creada
por 0.1.0 se adopta automáticamente (`stamp 0001` + `upgrade head`).

Backup, restore y retención: ver [`DATA.md`](DATA.md).

## 5. Configuración crítica

| Variable | Default | Efecto |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://...` | Conexión a PostgreSQL/SQLite (driver psycopg2 pinneado) |
| `CORS_ORIGINS` | orígenes locales | Debe ser explícito; `*` falla al arrancar |
| `SECRET_KEY` | placeholder | Sustituir en producción (warning al arrancar) |
| `MAX_HOSTS_PER_SCAN` | `1024` | Rechazo `422` por encima del límite |
| `MAX_PORTS_PER_SCAN` | `65535` | Rechazo `422` por encima del límite |
| `DEFAULT_SCAN_TIMEOUT` | `300` | Presupuesto por scan (segundos) |
| `LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`; inválido impide arrancar |
| `RESOLVE_HOSTNAMES` | `true` | DNS inverso; desactivar sin DNS |
| `AUTO_CREATE_SCHEMA` | `true` (dev) | `false` en contenedores: el esquema lo gestiona Alembic |
| `DATA_RETENTION_DAYS` | `30` | Días antes de purgar scans terminados; `0` desactiva |

## 6. Seguridad operativa

- No exponer `8001` a Internet sin autenticación/reverse proxy: la API no tiene
  auth de usuarios y permite lanzar escaneos.
- Mantener `SECRET_KEY` fuera del repositorio y rotarlo ante sospecha.
- Conceder solo `NET_RAW`/`NET_ADMIN` a `backend`/`celery`; `beat` no los
  necesita.
- Revisar que los targets pertenezcan a rangos autorizados antes de operar.
- No ejecutar escaneos agresivos en producción sin ventana y aprobación.

## 7. Escalado y límites

- `celery` con `--pool=solo` ejecuta una tarea a la vez; para concurrencia,
  cambiar el pool y dimensionar `max_concurrent_scans`.
- Los escaneos grandes consumen CPU/red: preferir subredes pequeñas y rangos de
  puertos acotados.
- `/api/metrics` calcula agregados por consulta; con históricos grandes conviene
  archivado o caché.
