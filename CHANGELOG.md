# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y versionado [SemVer](https://semver.org/lang/es/). El procedimiento de release y
el checklist están en [`docs/RELEASE.md`](docs/RELEASE.md).

## [Unreleased] — objetivo 0.1.0

### Added

- Motor de escaneo (`backend/app/core/`): TCP connect, TCP SYN, UDP y
  `comprehensive` (SYN + UDP con `DEFAULT_UDP_PORTS`), detección de servicios,
  fingerprint de SO y mapeo de red.
- API REST (`/api/scans`, `/api/schedules`) con paginación/filtros, ciclo de
  vida, cancelación y exportación `json`/`csv`/`xml`.
- WebSocket `/ws/scan/{scan_id}` con contrato versionado (`status`, `update`,
  `error`) y cierre en estados terminales.
- Schedules con `croniter`, `next_run_at`, Celery Beat cada 60 s y despachador
  idempotente.
- Frontend React/TypeScript: dashboard, detalle de scan con progreso en vivo,
  navegador de resultados con filtros/export y gestión de schedules.
- Observabilidad: logs JSON por línea con correlación `scan_id`/`task_id`,
  `GET /api/health` (con comprobación real de DB) y `GET /api/metrics`.
- Resiliencia: timeout por scan, idempotencia sobre estados terminales,
  aislamiento de fallos por host y mensajes de error seguros.
- Documentación: contrato REST/WS, runbook operativo, observabilidad, CI,
  checklist de release y guía de contenedores.

### Changed

- Contrato v1.0: separación `ScanSummary`/`ScanDetail`, protocolo correcto en
  resultados combinados y semántica de progreso unificada.
- Frontend con code-splitting por ruta y chunks de vendor (mayor chunk ~241 kB).
- Compose sin `version` obsoleto; backend de producción con `API_RELOAD=false`.
- Nivel de log configurable con `LOG_LEVEL` (`INFO` en prod, `DEBUG` en dev).

### Fixed

- P0 de auditoría: `COMPREHENSIVE` sin `udp_common` y etiquetado de protocolo
  UDP incorrecto.
- Cancelación/borrado coherentes entre API, tarea y WebSocket.
- Healthcheck del contenedor sin depender de `requests`.
- Tests deterministas: DNS inverso desactivable (`RESOLVE_HOSTNAMES`) y suite
  de backend en segundos, sin red real.
- Dry-run de release: PostgreSQL pinneado a `psycopg2` (SQLAlchemy 2.1 resolvía
  `psycopg` v3), entrada Celery corregida a `app.celery_app:celery_app`, los
  errores de import de tareas ya no se enmascaran como app dummy, el entrypoint
  parsea la URL de SQLAlchemy, healthcheck del frontend en `127.0.0.1` y
  healthchecks específicos para worker (ping) y beat (deshabilitado).

### Security

- Validación estricta de targets, rangos CIDR y puertos (1–65535) con rechazo
  `422`; límites `MAX_HOSTS_PER_SCAN=1024` y `MAX_PORTS_PER_SCAN=65535`.
- CORS con orígenes explícitos (sin `*`) y aviso de `SECRET_KEY` placeholder en
  producción.
- Contenedores `backend`/`celery` solo con `NET_RAW`/`NET_ADMIN`; `beat` sin
  capacidades; errores `500` genéricos sin filtrar internos.
- Alcance limitado a redes propias o con autorización explícita (DEC-004).

### Known limitations

Ver la sección 5 de [`docs/RELEASE.md`](docs/RELEASE.md): sin autenticación de
usuarios, sin E2E real en CI, sin exportador Prometheus/OpenTelemetry, sin
rotación de logs integrada y `celery --pool=solo` por defecto.
