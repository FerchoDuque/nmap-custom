# Release y checklist de hardening (PLAN-050)

Procedimiento de release para **nmap-custom**. Un release solo se aprueba con
el checklist completo y evidencia adjunta (comandos + resultado).

## 1. Versionado

- Esquema **SemVer** (`MAJOR.MINOR.PATCH`); el proyecto está en `0.1.0`.
- Fuentes de versión a mantener alineadas:
  - `backend/pyproject.toml` → `project.version`
  - `frontend/package.json` → `version`
  - `backend/app/main.py` → `FastAPI(version=...)` y `GET /`
  - `CHANGELOG.md` → mover `Unreleased` a la versión con fecha
  - `docs/CONTRACT.md` cuando cambie el contrato
- Tag de git: `vX.Y.Z` sobre el commit verificado.
- Cambios incompatibles de contrato ⇒ `MAJOR` (o `0.MINOR` en pre-1.0).

```bash
git tag -a v0.1.0 -m "Network Scanner 0.1.0"
git push origin v0.1.0
```

El workflow `release.yml` comprueba que el tag coincide con
`backend/pyproject.toml`, extrae la sección correspondiente de `CHANGELOG.md` y
crea el GitHub Release. Un tag publicado **no se mueve**: un fix se publica como
`0.1.1`.

## 1.1 Imágenes publicadas (GHCR)

```text
ghcr.io/ferchoduque/nmap-custom-backend
ghcr.io/ferchoduque/nmap-custom-frontend
```

- `main` → `edge` y `sha-<corto>`.
- Tag `vX.Y.Z` → `X.Y.Z`, `X.Y` y `latest`.
- Cada build adjunta SBOM y provenance (`mode=max`).
- Tras el primer push, poner los paquetes en **público** en GitHub → Packages
  (por defecto nacen privados, aunque el repo sea público).

## 2. Checklist de pre-release

### Calidad

- [ ] `make verify` (o `scripts/verify.ps1`) → **All checks passed**.
- [ ] Backend sin fallos: `pytest tests/api tests/core -q`.
- [ ] Frontend: `lint`, `typecheck`, `test:run`, `build`.
- [ ] Sin `print`/`TODO` bloqueantes ni tests marcados como skip sin motivo.
- [ ] `git status` limpio y rama sincronizada con `origin`.

### Seguridad y configuración

- [ ] `SECRET_KEY` distinto del placeholder (`uses_default_secret` falso).
- [ ] `CORS_ORIGINS` con orígenes explícitos (sin `*`).
- [ ] `ENV=production` con `API_RELOAD=false`.
- [ ] Límites revisados: `MAX_HOSTS_PER_SCAN`, `MAX_PORTS_PER_SCAN`,
      `DEFAULT_SCAN_TIMEOUT`, `MAX_CONCURRENT_SCANS`.
- [ ] `RESOLVE_HOSTNAMES` acorde al entorno (sin DNS ⇒ `false`).
- [ ] `LOG_LEVEL` acorde al entorno (`INFO` en producción, `DEBUG` solo en dev).
- [ ] `docker compose config` resuelve sin errores.
- [ ] Contenedores `backend`/`celery` solo con `NET_RAW`/`NET_ADMIN`; `beat`
      sin capacidades; ninguno en `privileged`.
- [ ] Sin secretos en el árbol (`git grep -i` de claves/tokens).
- [ ] Alcance autorizado confirmado por el operador (DEC-004).

### Base de datos

- [ ] Backup reciente de PostgreSQL.
- [ ] `make migrate` sin errores y `alembic current` en la revisión esperada.
- [ ] Migraciones probadas en una copia restaurada (no solo en la base viva).

### Documentación

- [ ] `plan.md` sin ítems `doing` no intencionales.
- [ ] `decisions.md` con las decisiones del ciclo.
- [ ] `bitacora.md` con verificación de la última iteración.
- [ ] `README`, `CHANGELOG.md`, `docs/CONTRACT.md`, `docs/RUNBOOK.md`, `docs/CI.md` y
      `docs/OBSERVABILITY.md` revisados contra el comportamiento real.
- [ ] Limitaciones conocidas vigentes (sección 5).

## 3. Smoke tests (dry-run documentado)

Ejecutar en un entorno autorizado. Registrar fecha, commit y resultados.

1. **Salud**: `curl -s http://localhost:8001/api/health` → `200`
   `{"status":"healthy","database":"connected"}`.
2. **Métricas**: `curl -s http://localhost:8001/api/metrics` → JSON con
   `scans.total` y totales.
3. **Crear scan** en una red de laboratorio:
   `POST /api/scans` con `target` autorizado y `scan_type=tcp_connect`.
4. **Progreso WS**: conectar `ws://localhost:8001/ws/scan/{id}` y verificar
   `status` inicial + `update` con `progress` creciente.
5. **Resultados**: `GET /api/scans/{id}` con `results/ports` coherentes.
6. **Export**: `POST /api/scans/{id}/export` en `json`, `csv` y `xml`.
7. **Cancelación**: `PATCH /api/scans/{id}` `{"status":"cancelled"}` sobre un
   scan activo.
8. **Schedules**: crear `POST /api/schedules`, verificar `next_run_at`, toggle y
   borrado; confirmar disparo dentro de 60 s con Beat activo.
9. **Errores**: target inválido → `422`; scan inexistente → `404`; el cliente no
   recibe trazas.
10. **Logs**: `scan_id`/`task_id` presentes en logs JSON y eventos
    `scan.started`/`scan.completed`.

Smoke tests automatizados disponibles sin red real (runbook):
`tests/core/test_resilience.py`, `tests/api/test_error_handling.py`,
`tests/api/test_system.py`.

### 3.1 Evidencia del dry-run (2026-11-14)

```text
Fecha/commit: 2026-11-14 / d997313 (fixes de wiring) + cierre documental
make verify: All checks passed (backend 205 passed, 1 skipped; frontend 67 passed; build OK)
docker compose config: docker-compose.yml y docker-compose.dev.yml -> exit 0
docker compose build: backend, celery, beat y frontend construidos
docker compose up -d: db/redis/backend/celery/frontend healthy; beat Up
Smoke 1 (salud):   GET http://localhost:8001/api/health -> 200 {"status":"healthy","database":"connected"}
Smoke 2 (métricas): GET /api/metrics -> JSON con scans.total/by_status/active y totales
Extra: frontend http://localhost/ -> 200; logs de backend y uvicorn.access en JSON
Smoke 3-10: diferidos a entorno autorizado (decisión del operador; sin escaneos reales)
Incidencias: 6 fallos de wiring detectados y corregidos (driver DB, Celery, entrypoint,
             healthchecks de frontend/worker/beat y logs de Uvicorn)
Rollback: no ejecutado (sin migraciones destructivas en esta iteración)
Tag: v0.1.0 (anotado, sobre el commit de cierre de esta iteración)
Aprobado por: operador (alcance limitado a salud/métricas)
```


## 4. Rollback

1. Detener servicios: `make down`.
2. Volver al tag estable: `git checkout vX.Y.Z` (o rama de release).
3. Reconstruir: `make build`.
4. **Si hubo migraciones con pérdida de datos**: restaurar el backup previo
   (ver sección *Backup & Restore* en [`DOCKER.md`](DOCKER.md)) antes de
   arrancar.
5. Arrancar: `make up` y repetir los smoke tests 1–2.
6. Registrar el incidente en `bitacora.md` y, si aplica, abrir una decisión
   (`DEC-xxx`) con la causa raíz.

Sin migraciones destructivas, el rollback de imagen es suficiente; las tareas
en vuelo pueden reintentarse porque los scans terminales no se reejecutan.

## 5. Limitaciones conocidas (release 0.1.0)

- Sin autenticación de usuarios ni multi-tenancy: la API debe quedar en red
  privada o detrás de un proxy con auth.
- Sin E2E real en CI: WebSocket, red y Beat se validan manualmente en entorno
  autorizado (DEC-004).
- Sin exportador Prometheus/OpenTelemetry; `/api/metrics` es el contrato estable.
- Nivel de log configurable con `LOG_LEVEL` (`INFO` en prod, `DEBUG` en dev);
  no hay rotación de logs integrada (gestionarla en el orquestador).
- `celery` corre con `--pool=solo` por defecto (una tarea a la vez).
- Escaneos SYN/UDP/OS requieren Linux con capacidades; en otros entornos usar
  `tcp_connect`.
- Deuda de rendimiento del frontend resuelta con code-splitting; revisar el
  tamaño de chunks si se añaden librerías pesadas.
- Warnings de deprecación de Pydantic v1-style/FastAPI `on_event` y
  `datetime.utcnow()` son no bloqueantes para 0.1.0.

## 6. Evidencia del dry-run

Registrar en la entrada de release de `bitacora.md`:

```text
Fecha/commit:
make verify:
docker compose config:
Smoke tests (1-10):
Incidencias y rollback probado:
Aprobado por:
```
