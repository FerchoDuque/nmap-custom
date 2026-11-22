# bitacora.md — Registro de iteraciones (loop)

> Trazabilidad cronológica de trabajo. Ver protocolo en [`agents.md`](agents.md), backlog/grafo en [`plan.md`](plan.md) y decisiones en [`decisions.md`](decisions.md).

## Convenciones

- Orden **cronológico descendente** (más reciente arriba).
- Una entrada por iteración/sesión relevante.
- Incluir siempre: objetivo (`PLAN-xxx`), acciones, verificación (o limitación), hallazgos y siguiente paso.
- Referenciar archivos, comandos y decisiones (`DEC-xxx`) cuando aplique.

## Plantilla de entrada

```md
## YYYY-MM-DD HH:MM (TZ) — Rol/Agente
- **Objetivo (Plan ID):** 
- **Contexto/insumos:** 
- **Acciones realizadas:** 
  - 
- **Archivos tocados:** 
  - 
- **Verificación:** 
  - Comando/prueba: resultado
- **Hallazgos / riesgos / deuda:** 
  - 
- **Decisiones:** (DEC-xxx o "ninguna / pendiente")
- **Siguiente paso:** 
```

---

## 2026-11-20 — Infra/Docs (PLAN-060/061: madurez de repositorio, licencia y cadena de suministro)

- **Objetivo (Plan ID):** PLAN-060 (CI/CD y cadena de suministro) y PLAN-061 (licencia, gobernanza y metadatos).
- **Contexto/insumos:** auditoría del repo público: CI fallando en 0 s desde el primer push, sin `LICENSE`, deps sin lock (el bug de `psycopg` ya lo demostró), sin CodeQL/Dependabot, sin imágenes ni release.
- **Acciones realizadas:**
  - **CI:** `concurrency`, `timeout-minutes`, `workflow_call` y job `Compose config`; install desde `requirements-dev.txt`.
  - **Seguridad/automatización:** `codeql.yml` (Python + JS/TS, `security-extended`), `dependabot.yml` (pip/npm/actions/docker) y `docker.yml` (GHCR, SBOM, provenance).
  - **Release:** `release.yml` reejecuta CI, compara el tag con `pyproject` y publica notas extraídas del CHANGELOG (`scripts/changelog_section.py`).
  - **Reproducibilidad:** `pyproject` completo + `uv.lock` como única fuente; CI y Docker exportan los pins con hashes en el build (sin `requirements*.txt` versionados); `make lock`.
  - **Licencia/gobernanza:** `LICENSE` GPL-3.0 (DEC-016), `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, plantillas de issue/PR, badges y roadmap real en README.
  - **Protection:** `main` con PR + checks obligatorios, sin force-push ni borrado, `enforce_admins=false` (mantenedor único).
- **Archivos tocados:** `.github/{workflows/{ci,codeql,docker,release}.yml,dependabot.yml,ISSUE_TEMPLATE/*,PULL_REQUEST_TEMPLATE.md}`, `scripts/changelog_section.py`, `backend/{pyproject.toml,uv.lock,requirements*.txt}`, `backend/tests/core/{test_workflows,test_versions,test_dependencies,test_changelog_section}.py`, `Makefile`, `README.md`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `docs/{CI,RELEASE}.md`, `decisions.md`, `plan.md`, `bitacora.md`.
- **Verificación:**
  - `pytest tests/api tests/core -q` → **226 passed, 1 skipped** (incluye los 4 archivos de test nuevos).
  - `docker compose config` (prod/dev) → exit 0.
  - CI en GitHub: runs `44801239036` y `44801604225` → **success**; tras el push de 0.2.0, run `44806348488` → **success** (40 s), `CodeQL` `44806348261` → **success** y `Docker` `44806348666` → **success** (build + push a GHCR con SBOM/provenance).
  - Imágenes verificadas con token anónimo: `ghcr.io/ferchoduque/nmap-custom-{backend,frontend}:main` y `:sha-8c55cc0` **públicas**.
  - **Limitación:** `docker build` no se pudo repetir en local (Docker Desktop detenido); la construcción real la validó `docker.yml`.
- **Hallazgos / riesgos / deuda:**
  - `python-nmap` es GPL-3.0: se eligió GPL-3.0 para no reescribir la integración; una licencia permisiva exigiría sustituirlo.
  - GHCR crea paquetes privados por defecto: hay que hacerlos públicos tras el primer push.
  - `enforce_admins=false` permite saltarse los checks: aceptado para un mantenedor único, revisable cuando haya más.
  - FastAPI/Celery resueltos a versiones actuales (FastAPI 0.165, Celery 5.7): CI es la validación real, no el entorno local.
- **Decisiones:** DEC-016.
- **Siguiente paso:** PLAN-062 (Alembic + backups), PLAN-063 (auth/RBAC/audit), PLAN-064 (guardrails) y PLAN-065 (E2E `lab`).

## 2026-11-20 — Infra/QA (CI rojo corregido y actions actualizadas)

- **Objetivo:** el CI del repo público nunca se había ejecutado (3 runs fallidos en 0 s).
- **Contexto/insumos:** `gh run list` mostró `failure` en 0 s; `yaml.safe_load` del workflow fallaba en la línea 31.
- **Acciones realizadas:**
  - Causa raíz: `DATABASE_URL: sqlite:///:memory:` sin comillas; el segundo `:` rompe el YAML.
  - TDD: `backend/tests/core/test_workflows.py` valida que todos los workflows son YAML parseable, declaran `jobs` y que cada step tiene `uses` o `run` (rojo antes del fix).
  - Fix: valor entre comillas en `ci.yml`.
  - Actualización: `actions/checkout@v5`, `actions/setup-python@v6`, `actions/setup-node@v5` (Node 24) para eliminar el aviso de deprecación.
- **Archivos tocados:** `.github/workflows/ci.yml`, `backend/tests/core/test_workflows.py`, `bitacora.md`, `plan.md`.
- **Verificación:**
  - `pytest tests/core/test_workflows.py tests/core/test_compose_config.py -q` → **10 passed**.
  - Run `44801239036` → **success** (backend 40 s, frontend 1m59s); run posterior `44801604225` → **success** (32 s / 52 s) **sin annotations**.
- **Hallazgos / riesgos / deuda:**
  - El CI solo cubre tests/lint/typecheck/build; no valida compose, no publica imágenes ni usa lockfiles (deuda para 0.2.0).
  - Un workflow inválido falla en 0 s y no avisa: ahora hay test de regresión.
- **Decisiones:** ninguna.
- **Siguiente paso:** roadmap 0.2.0 (ver plan) — CI con gates, migraciones, auth/guardrails y E2E en red aislada.

## 2026-11-14 — Release (publicación en GitHub)

- **Objetivo:** publicar el proyecto y el tag `v0.1.0` en un repositorio remoto.
- **Contexto/insumos:** `gh` autenticado como `FerchoDuque` (scopes `repo`, `workflow`); sin remotos configurados y sin repo previo con ese nombre.
- **Acciones realizadas:**
  - `gh repo create nmap-custom --public --source . --remote origin --push` → crea `FerchoDuque/nmap-custom` (público), añade `origin` y sube `main`.
  - `git push origin v0.1.0` → publica el tag anotado.
- **Verificación:**
  - `gh repo view` → `visibility: PUBLIC`, `isPrivate: false`, rama por defecto `main`.
  - `gh api repos/.../tags` → `v0.1.0`.
  - `git ls-remote --tags origin` → `refs/tags/v0.1.0` apunta a `42c30d8` (tag anotado).
  - `git status -sb` → `## main...origin/main` sin cambios pendientes.
- **Hallazgos / riesgos / deuda:**
  - El repositorio es público: no hay secretos versionados (solo `.env.example`/`.env.docker` con valores de ejemplo) y `SECRET_KEY` sigue siendo placeholder (el backend emite warning al arrancar).
  - Faltan metadatos de repositorio: descripción, topics y `LICENSE` (el proyecto no declara licencia explícita).
  - El tag no cubre los smoke 3–10; cualquier defecto posterior se publica como `0.1.1` sin mover `v0.1.0`.
- **Decisiones:** ninguna nueva.
- **Siguiente paso:** decidir licencia y metadatos del repo; smoke 3–10 en entorno autorizado.

## 2026-11-14 — Release (tag v0.1.0)

- **Objetivo:** publicar `v0.1.0` tras el dry-run 1–2 aprobado.
- **Acciones realizadas:**
  - `CHANGELOG.md`: `Unreleased — objetivo 0.1.0` → `[0.1.0] — 2026-11-14`.
  - `docs/RELEASE.md` §3.1: evidencia incluye el tag; `plan.md` refleja el cierre.
  - Verificadas las fuentes de versión: `backend/pyproject.toml`, `frontend/package.json` y `FastAPI(version=...)`/`GET /` en `0.1.0`.
- **Verificación:** `git tag -n` y `git show v0.1.0 --stat`; árbol limpio y stack healthy al momento del tag.
- **Hallazgos / riesgos / deuda:** el tag no valida los smoke 3–10; si esos flujos revelan defectos, se corregirá y publicará `0.1.1` (no se mueve el tag).
- **Aprobado por:** operador.
- **Siguiente paso:** smoke 3–10 en entorno autorizado (DEC-004).

## 2026-11-14 — Infra/QA (PLAN-050: dry-run de release y wiring corregido)

- **Objetivo (Plan ID):** PLAN-050 (dry-run real: build, up, smoke 1–2).
- **Contexto/insumos:** Docker Desktop se inició con aprobación del operador; el alcance de validación se limitó a salud/métricas (sin escaneos reales).
- **Acciones realizadas:**
  - `docker compose build` (backend, celery, beat, frontend) y `up -d`; verificación de `ps` y smoke 1–2.
  - **6 fallos de wiring detectados y corregidos** (TDD donde era posible):
    1. **DB:** SQLAlchemy 2.1 resuelve `postgresql://` a `psycopg` v3 (no instalado). Se fija `postgresql+psycopg2://` en `config.py`, compose prod/dev y `.env.docker`.
    2. **Celery CLI:** `-A app.celery_app` buscaba el atributo `celery`; ahora `-A app.celery_app:celery_app` (worker y beat, prod/dev).
    3. **Fallback silencioso:** `celery_app.py` convertía cualquier `ImportError` (incluido el fallo de DB) en `_DummyCeleryApp`; ahora el dummy solo aplica si falta el paquete `celery` y los imports de `app.tasks` fallan rápido.
    4. **Entrypoint:** pasaba la URL SQLAlchemy a `psycopg2.connect`; ahora usa `make_url` y omite la espera en backends no PostgreSQL.
    5. **Healthchecks:** frontend usaba `localhost` (IPv6) → `127.0.0.1`; worker valida con `celery inspect ping`; beat lo tiene deshabilitado (no sirve HTTP).
    6. **Logs:** `uvicorn.access/error` quedaban en texto plano; `include_uvicorn=True` los enruta al formatter JSON.
  - Tests de regresión: `tests/core/test_compose_config.py` (entrada Celery, `version` obsoleto, driver psycopg2, parseo del entrypoint) y `tests/core/test_celery_app.py` (app real cuando Celery está instalado; skip si no).
- **Archivos tocados:** `backend/app/{config,main,celery_app}.py`, `backend/app/core/logging_utils.py`, `backend/docker-entrypoint.sh`, `frontend/Dockerfile`, `docker-compose{,.dev}.yml`, `.env.docker`, `README.md`, `backend/README.md`, `docs/RUNBOOK.md`, `docs/OBSERVABILITY.md`, `docs/RELEASE.md`, `CHANGELOG.md`, `decisions.md`, `plan.md`, `bitacora.md` y los dos tests nuevos.
- **Verificación:**
  - `docker compose ps` → db/redis/backend/celery/frontend **healthy**; beat `Up`.
  - `GET /api/health` → `200 {"status":"healthy","database":"connected"}`; `GET /api/metrics` → JSON con `scans.total`/`by_status`/`active`; frontend `200`; logs JSON (app y `uvicorn.access`).
  - `pytest tests/api tests/core` → **205 passed, 1 skipped**; `verify.ps1` → **All checks passed** (frontend 67).
  - Worker procesó `dispatch_due_schedules_task` (`{'dispatched': 0}`) con Beat activo.
- **Hallazgos / riesgos / deuda:**
  - Smoke 3–10 (scan real, WS, export, schedules, cancelación) quedan para entorno autorizado (DEC-004); el usuario limitó esta validación a salud/métricas.
  - El healthcheck del worker depende de `inspect ping` y del nombre `celery@$HOSTNAME`; si se cambia `--hostname`, ajustar el check.
  - El stack queda levantado en local; `make down` para detenerlo.
- **Decisiones:** DEC-015.
- **Siguiente paso:** completar smoke 3–10 en entorno autorizado, fechar `CHANGELOG` y crear tag `v0.1.0` con aprobación.

## 2026-11-14 — Docs/Release (PLAN-050: CHANGELOG y fuentes de versión)

- **Objetivo (Plan ID):** PLAN-050 (release readiness).
- **Contexto/insumos:** no existía `CHANGELOG.md` ni un lugar único que agrupara los cambios de `0.1.0`; `docs/RELEASE.md` listaba fuentes de versión pero no el changelog.
- **Acciones realizadas:**
  - `CHANGELOG.md` en formato Keep a Changelog con `Unreleased — objetivo 0.1.0` y secciones Added/Changed/Fixed/Security/limitaciones, resumiendo motor, API/WS, schedules, frontend, observabilidad, resiliencia, seguridad y docs.
  - README: índice documental incluye el changelog.
  - `docs/RELEASE.md`: §1 añade `CHANGELOG.md` como fuente de versión (mover `Unreleased` con fecha) y el checklist de documentación lo incluye.
  - `plan.md`: evidencia de PLAN-050 actualizada.
- **Archivos tocados:** `CHANGELOG.md` (nuevo), `README.md`, `docs/RELEASE.md`, `plan.md`, `bitacora.md`.
- **Verificación:** revisión cruzada del contenido con `plan.md`/`decisions.md` y versiones `0.1.0` en `backend/pyproject.toml`, `frontend/package.json` y `backend/app/main.py`. Cambio documental sin código ejecutable: no aplica TDD (excepción justificada en `agents.md` §4).
- **Hallazgos / riesgos / deuda:** el changelog quedará como `Unreleased` hasta que el dry-run de PLAN-050 se apruebe; entonces se fechará y se creará el tag `v0.1.0`.
- **Decisiones:** ninguna nueva.
- **Siguiente paso:** dry-run con Docker activo y cierre de PLAN-050.

## 2026-11-14 — Backend/Observabilidad (deuda PLAN-040: nivel de log configurable)

- **Objetivo:** cerrar la deuda "nivel de log fijo en `INFO`" detectada al cerrar PLAN-040/DEC-012.
- **Contexto/insumos:** `main.py` llamaba `configure_logging(level="INFO")` con un literal; no había forma de subir a `DEBUG` en diagnóstico ni de validar un valor erróneo antes de arrancar.
- **Acciones realizadas:**
  - **TDD:** `TestLogLevel` en `tests/core/test_config.py` (default `INFO`, normalización ` debug ` → `DEBUG`, rechazo de `verbose`/`TRACE`/`10`/vacío), en rojo antes de implementar.
  - **Config:** `Settings.log_level` con `field_validator(mode="before")` y `VALID_LOG_LEVELS`; inválido ⇒ `ValidationError` que impide arrancar.
  - **Arranque:** `main.py` usa `settings.log_level` en `configure_logging`.
  - **Entornos:** `LOG_LEVEL=INFO` en prod (`.env.docker`, compose backend/celery) y `DEBUG` en dev; `LOG_LEVEL=INFO` en `backend/.env.example`; `RESOLVE_HOSTNAMES` añadido también a `.env.docker` por consistencia.
  - **Docs:** contrato §3.7, `docs/OBSERVABILITY.md` (sección "Nivel de log"), `docs/RUNBOOK.md` (tabla), `docs/RELEASE.md` (checklist y limitaciones), README y DEC-012 (actualización).
- **Archivos tocados:** `backend/app/config.py`, `backend/app/main.py`, `backend/tests/core/test_config.py`, `backend/.env.example`, `.env.docker`, `docker-compose.yml`, `docker-compose.dev.yml`, `docs/CONTRACT.md`, `docs/OBSERVABILITY.md`, `docs/RUNBOOK.md`, `docs/RELEASE.md`, `README.md`, `decisions.md`, `plan.md`, `bitacora.md`.
- **Verificación:**
  - `pytest tests/core/test_config.py tests/core/test_logging_utils.py tests/api/test_system.py -q` → **29 passed**.
  - `docker compose -f docker-compose.yml config --quiet` y `.dev.yml` → **exit 0**.
  - `verify.ps1` completo → **All checks passed** (backend **196 passed**, frontend **67 passed**, build OK).
- **Hallazgos / riesgos / deuda:**
  - Un `LOG_LEVEL` inválido ahora es un fallo de arranque deliberado (fail-fast); hay que corregir el `.env` en lugar de degradar silenciosamente.
  - No hay rotación de logs integrada; se delega en el orquestador (documentado en RELEASE).
  - Queda como única deuda de observabilidad el exportador Prometheus/OpenTelemetry.
- **Decisiones:** actualización de DEC-012 (sin nueva DEC).
- **Siguiente paso:** reejecutar `verify.ps1`, validar `docker compose config` y cerrar PLAN-050 cuando Docker esté disponible.

## 2026-11-13 — Producto/Infra (PLAN-043: alcance de `electron/`)

- **Objetivo (Plan ID):** PLAN-043 (decisión explícita sobre el empaquetado Electron).
- **Contexto/insumos:** `electron/` existía como directorio vacío y no versionado (`git ls-files electron` vacío); el README lo anunciaba como "future" y el roadmap lo listaba como pendiente, lo que sugería un entregable inexistente.
- **Acciones realizadas:**
  - **DEC-014:** empaquetado Electron **aplazado** fuera del alcance de 0.1.0; no se mantiene placeholder activo y se reevaluará solo con una `DEC` nueva que defina alcance, distribución (firma/auto-update) y coste.
  - README: árbol de directorios y roadmap marcan Electron como aplazado (DEC-014).
  - Plan/grafo: `PLAN-043` → `done`, nodo `EL` anotado con el aplazamiento y backlog actualizado.
- **Archivos tocados:** `decisions.md`, `README.md`, `plan.md`, `bitacora.md`.
- **Verificación:**
  - `Test-Path electron` → `True` (vacío) y `git ls-files electron` → sin archivos.
  - Revisión cruzada: el alcance declarado en `plan.md` §1 ya excluía Electron del alcance inmediato.
  - Cambio documental sin código ejecutable: no aplica TDD (excepción justificada según `agents.md` §4).
- **Hallazgos / riesgos / deuda:** si se retoma Electron habrá que crear el proyecto desde cero; no hay impacto en el release 0.1.0 ni dependencias bloqueadas.
- **Decisiones:** DEC-014.
- **Siguiente paso:** cierre de PLAN-050 con Docker activo y validación real de schedules (PLAN-023) en entorno autorizado.

## 2026-11-13 — Docs/Release (PLAN-042 cerrado, PLAN-050 iniciado)

- **Objetivo (Plan ID):** PLAN-042 (runbooks y documentación profesional) y PLAN-050 (checklist de release y hardening).
- **Contexto/insumos:** existían `docs/DOCKER.md`, `docs/CI.md`, `docs/OBSERVABILITY.md` y el contrato, pero no había un runbook por síntoma ni un procedimiento de release verificable. Los compose conservaban `version: '3.8'` (obsoleto en Compose v2) y el backend de producción arrancaba con `API_RELOAD` por defecto (`true`).
- **Acciones realizadas:**
  - **Runbook:** `docs/RUNBOOK.md` con mapa de servicios/puertos (backend `8001→8000`, frontend `80`), ciclo de vida (`make prod/dev/ps/logs`), chequeo de salud (`/api/health`, `/api/metrics`), diagnóstico por síntoma (500, scans `pending`, `failed`, cancelación, schedules, logs, DB/migraciones), configuración crítica y seguridad operativa.
  - **Release:** `docs/RELEASE.md` con SemVer/tagging (`vX.Y.Z`), checklist de calidad/seguridad/DB/documentación, smoke tests 1–10 (incluye WS, export, cancelación y schedules), rollback con backup y limitaciones conocidas de 0.1.0.
  - **README:** índice de documentación, variables de resiliencia (`MAX_*`, `DEFAULT_SCAN_TIMEOUT`, `RESOLVE_HOSTNAMES`) y referencias a runbook/release en seguridad.
  - **Compose:** eliminado `version:` obsoleto en `docker-compose.yml` y `docker-compose.dev.yml`; añadido `API_RELOAD=false` al backend de producción.
- **Archivos tocados:**
  - `docs/RUNBOOK.md`, `docs/RELEASE.md` (nuevos)
  - `README.md`, `plan.md`, `bitacora.md`
  - `docker-compose.yml`, `docker-compose.dev.yml`
- **Verificación:**
  - `docker compose -f docker-compose.yml config --quiet` → **exit 0**; `docker-compose.dev.yml` → **exit 0** (sin aviso de `version`).
  - Comandos citados en el runbook (`prod`, `dev`, `ps`, `logs*`, `restart*`, `migrate`, `shell-db`) contrastados con los targets reales del `Makefile`.
  - Rutas/anclas revisadas contra `docs/DOCKER.md` (sección *Backup & Restore* por nombre, no por ancla).
  - No se ejecutaron `build`/`up` ni smoke tests reales.
- **Hallazgos / riesgos / deuda:**
  - **Bloqueo:** Docker Desktop no está corriendo (`docker info` falla con `dockerDesktopLinuxEngine`), así que el dry-run de PLAN-050 (build/up + smoke tests 1–2) queda pendiente; los smoke tests 3–10 requieren además un entorno autorizado (DEC-004).
  - La documentación de release incluye intencionadamente limitaciones vigentes: sin auth/multi-tenancy, sin E2E en CI, sin exportador Prometheus, nivel de log fijo y `celery --pool=solo`.
  - Warnings de deprecación (Pydantic v1-style, `on_event`, `datetime.utcnow()`) se documentan como no bloqueantes para 0.1.0.
- **Decisiones:** sin `DEC` nueva; se consolidan DEC-004 (alcance), DEC-012 (observabilidad) y DEC-013 (resiliencia) en los procedimientos.
- **Siguiente paso:** con Docker activo, `make build`/`make up` y smoke tests 1–2; después, en entorno autorizado, smoke tests 3–10 y cierre de PLAN-050 con evidencia en `docs/RELEASE.md` §6.

## 2026-11-13 — Backend/QA (PLAN-032: resiliencia, timeouts e idempotencia)

- **Objetivo (Plan ID):** PLAN-032 (degradación controlada, mensajes seguros e idempotencia).
- **Contexto/insumos:** `perform_scan_task` no tenía timeout ni protección ante entregas duplicadas; un fallo al escanear un host abortaba el scan completo; los errores no controlados devolvían el traceback por defecto de FastAPI; `socket.gethostbyaddr` se ejecutaba sin control y hacía que los tests dependieran de DNS real (~9 s por host).
- **Acciones realizadas:**
  - **TDD:** `tests/core/test_resilience.py` (idempotencia, timeout, truncado de errores, persistencia y aislamiento por host) y `tests/api/test_error_handling.py` (`500` genérico, `404`/`422` con detalle), en rojo antes de implementar.
  - **Runner testeable:** extraído `execute_scan(db, scan_id, task_id, scanner=None, update_state=None, timeout=None)` en `app/tasks.py`; `perform_scan_task` queda como wrapper Celery delgado.
  - **Timeout:** `asyncio.wait_for` con `settings.default_scan_timeout` (o inyectado), `ScanTimeoutError` y estado `failed` con mensaje `Scan exceeded the configured timeout of Ns`.
  - **Idempotencia:** scans `completed`/`failed`/`cancelled` no se re-ejecutan (`{"status": "skipped"}`, evento `scan.skipped`); scan inexistente → `not_found`.
  - **Errores seguros:** `_safe_error_message` trunca a 500 caracteres y enmascara `SQLAlchemyError`; handler global en `main.py` responde `500 {"detail": "Internal server error"}` y loguea el traceback.
  - **Aislamiento por host:** `NetworkScanner.scan` captura errores por host, loguea, continúa y reporta `hosts_failed`.
  - **DNS inverso configurable:** `RESOLVE_HOSTNAMES` (default `true`) + `_resolve_hostname` sin excepciones; tests con `resolve_hostnames=False`, eliminando la dependencia de red y bajando la suite de ~73 s a ~2.4 s.
- **Archivos tocados:**
  - `backend/app/tasks.py`, `backend/app/main.py`, `backend/app/core/scanner.py`, `backend/app/config.py`, `backend/.env.example`
  - `backend/tests/core/test_resilience.py` (nuevo), `backend/tests/api/test_error_handling.py` (nuevo), `backend/tests/core/test_scanner.py`
  - `docs/CONTRACT.md`, `docs/OBSERVABILITY.md`, `README.md`, `plan.md`, `decisions.md`, `bitacora.md`
- **Verificación:**
  - `pytest tests/core/test_resilience.py tests/api/test_error_handling.py tests/core/test_scanner.py` → **20 passed** en 0.58 s.
  - `pytest tests/api tests/core -q` → **190 passed** en **2.39 s** (antes 175 en ~37 s).
  - Todo con SQLite in-memory, mocks/fakes y sin DNS/red real (DEC-004/010).
- **Hallazgos / riesgos / deuda:**
  - El timeout acota también una resolución DNS colgada (dentro del presupuesto del scan), pero no hay cancelación cooperativa del motor a mitad de socket.
  - No hay reintentos automáticos de la tarea: se prioriza idempotencia y visibilidad (`failed`) sobre reejecución silenciosa.
  - `hosts_failed` se reporta en resultados y logs, pero no se persiste como columna (no requiere migración).
- **Decisiones:** DEC-013 (timeout acotado, idempotencia terminal, errores seguros y DNS configurable).
- **Siguiente paso:** PLAN-042 (runbooks) y PLAN-050 (checklist de release), más validación real de schedules en entorno autorizado.

## 2026-11-13 — Infra/Backend (PLAN-040: observabilidad, health y métricas)

- **Objetivo (Plan ID):** PLAN-040 (logging estructurado con correlación, health útil y métricas básicas).
- **Contexto/insumos:** `main.py` usaba `logging.basicConfig` con texto libre; `tasks.py` logueaba sin `scan_id`/`task_id`; `/api/health` devolvía `healthy` fijo sin tocar la base y no existían métricas de operación. El `HEALTHCHECK` del Dockerfile importaba `requests`, que no está en `requirements.txt`.
- **Acciones realizadas:**
  - **TDD logging:** `tests/core/test_logging_utils.py` define formato JSON, correlación, traceback, override de `scan_id` e idempotencia; implementado `app/core/logging_utils.py` con `JsonFormatter`, `ScanLoggerAdapter`, `get_scan_logger(scan_id, task_id, logger=None)` y `configure_logging`.
  - **Compatibilidad Python 3.14:** el intérprete mantiene `exc_info=True` como booleano en `LogRecord`; el formatter resuelve bools vía `sys.exc_info()` y omite el campo si no hay excepción activa (sin `TypeError`).
  - **Correlación en tareas:** `tasks.py` emite `scan.started`, `scan.completed` (hosts/puertos), `scan.failed`, `scan.not_found` y `scan.progress_error`; `scan.task_id` usa el id resuelto defensivamente (fallback sin Celery).
  - **Health y métricas:** `api/system.py` con `/api/health` (`SELECT 1`, `503` + `degraded` si la DB falla) y `/api/metrics` (total, `by_status`, `active`, `hosts_up_total`, `ports_found_total` con `coalesce`); `main.py` incluye el router y configura logging JSON al arrancar.
  - **Docker/healthcheck:** `backend/Dockerfile` usa `urllib.request` de la stdlib, sin dependencia de `requests`.
  - **Docs:** contrato §3.6 (operación) y §3.7 (logging), `docs/OBSERVABILITY.md`, README y `docs/DOCKER.md`.
- **Archivos tocados:**
  - `backend/app/core/logging_utils.py`, `backend/app/api/system.py` (nuevos)
  - `backend/app/main.py`, `backend/app/tasks.py`, `backend/Dockerfile`
  - `backend/tests/core/test_logging_utils.py`, `backend/tests/api/test_system.py` (nuevos)
  - `docs/CONTRACT.md`, `docs/OBSERVABILITY.md` (nuevo), `docs/DOCKER.md`, `README.md`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `pytest tests/core/test_logging_utils.py tests/api/test_system.py -q` → **13 passed**.
  - `pytest tests/api tests/core -q` → **175 passed** (antes 162).
  - Sin red real ni contenedores; DB simulada con SQLite in-memory y `MagicMock` para el caso degradado (DEC-004/010).
- **Hallazgos / riesgos / deuda:**
  - Los tests del adapter ahora inyectan un logger dedicado (`get_scan_logger(..., logger=...)`); el logger compartido `app.scans` queda para runtime.
  - Nivel de log fijo en `INFO` al arrancar; hacerlo configurable por entorno queda como deuda.
  - Sin exportador Prometheus/OpenTelemetry; `/api/metrics` es el contrato estable por ahora.
  - El healthcheck del Dockerfile no se validó construyendo la imagen (sin Docker en este entorno).
- **Decisiones:** DEC-012 (JSON logs stdlib, health 503 y métricas agregadas).
- **Siguiente paso:** PLAN-032 (resiliencia/errores) y PLAN-042/050 (runbooks y release), más validación real de schedules (PLAN-023) en entorno autorizado.

## 2026-11-13 — Frontend (deuda PLAN-022: code-splitting del bundle)

- **Objetivo (Plan ID):** PLAN-022 (deuda de rendimiento: bundle principal > 500 kB).
- **Contexto/insumos:** el build emitía un único `index-*.js` de ~530 kB y el aviso de Vite; todas las rutas se importaban estáticamente.
- **Acciones realizadas:**
  - **Rutas lazy:** `ScanDetails`, `ResultsBrowser` y `Schedules` con `React.lazy` + `Suspense` y fallback `> LOADING_MODULE...`; `Dashboard` queda eager por ser la entrada.
  - **Chunks manuales:** `manualChunks` separa `react`, `react-router`, `mui`, `mui-icons`, `http` (axios), `state` (zustand) y `vendor`.
- **Archivos tocados:** `frontend/src/App.tsx`, `frontend/vite.config.ts`, `docs/CI.md`, `plan.md`, `bitacora.md`.
- **Verificación:**
  - `npm run build` → OK **sin aviso de chunk > 500 kB**; mayor chunk `mui` **241.02 kB** (gzip 72.41), entrada **23.87 kB**, rutas lazy de 6.9–12.3 kB.
  - `npm run lint` → OK; `npx tsc --noEmit` → OK; `npm run test:run` → **67 passed**.
- **Hallazgos / riesgos / deuda:**
  - `recharts`/`d3`/`@tanstack/react-table` siguen como dependencias sin uso; candidatos a retirar si no se usan en visualizaciones futuras.
  - El fallback de suspensión es básico; suficiente para el baseline.
- **Decisiones:** ninguna nueva; ajuste de build alineado con DEC-009 (UI) sin cambiar contrato.
- **Siguiente paso:** PLAN-040 (observabilidad) y validación de disparo real de schedules (PLAN-023) en entorno autorizado.

## 2026-11-13 — Frontend/QA (PLAN-021: validación funcional con pruebas de componentes)

- **Objetivo (Plan ID):** PLAN-021 (validación funcional del flujo UI principal sin red real).
- **Contexto/insumos:** el flujo estaba implementado y cubierto por utilidades puras, pero no había pruebas DOM; no se podía verificar creación, progreso WS ni cancelación a nivel de componente sin un backend real.
- **Acciones realizadas:**
  - **Harness DOM:** instalados `jsdom` 24 (fijado por compatibilidad con Vitest 1.6/Node 22), `@testing-library/react`, `@testing-library/user-event` y `@testing-library/jest-dom` 6; entorno `jsdom` por archivo (`// @vitest-environment jsdom`) y `cleanup` explícito.
  - **`ScanDialog` (5 pruebas):** target inválido bloquea envío; target requerido; límite de 1024 hosts; envío con valores del formulario y cierre; error de API mantiene el diálogo abierto y reactiva el botón.
  - **`ScanDetails` (4 pruebas):** carga y conexión WS; aplicación de progreso/host desde `update`; estado terminal recarga resultados, desconecta y oculta cancelar; cancelación llama `PATCH {status: cancelled}` y recarga.
  - **`Dashboard` (3 pruebas):** listado de scans recientes, estado vacío y creación desde el diálogo con recarga de la lista.
  - **TDD de validación:** test rojo para el límite total de puertos (`1-40000,1-40000`) y ajuste de `validatePortRange` con `MAX_PORTS_PER_SCAN=65535`, alineado con backend.
- **Archivos tocados:**
  - `frontend/src/components/ScanDialog.test.tsx`, `frontend/src/components/Dashboard/Dashboard.test.tsx`, `frontend/src/components/ScanDetails/ScanDetails.test.tsx` (nuevos)
  - `frontend/src/utils/validation.ts`, `frontend/src/utils/validation.test.ts`
  - `frontend/package.json`, `frontend/package-lock.json`
  - `docs/UI.md`, `docs/CI.md`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `npx vitest run` → **67 passed** (8 archivos; incluye 12 pruebas DOM).
  - `npm run lint` → OK; `npx tsc --noEmit` → OK; `npm run build` → OK (aviso de bundle ~530 kB).
  - API y WebSocket mockeados; sin red, DNS ni backend real (DEC-004/010).
- **Hallazgos / riesgos / deuda:**
  - Las pruebas de componentes añaden ~15 s al pipeline (colecta de MUI/jsdom), pero son deterministas.
  - La validación E2E con backend real sigue pendiente y requiere entorno autorizado.
  - `jsdom` se fijó en 24.1.3: jsdom 31 fallaba al cargar `undici` en este entorno (Node 22.13/Vitest 1.6).
- **Decisiones:** ninguna nueva; DEC-010 aplicada (mocks/fixtures, sin red real).
- **Siguiente paso:** code-splitting del bundle (deuda PLAN-022), validación de disparo real de schedules (PLAN-023) y observabilidad (PLAN-040).

## 2026-11-13 — Infra/QA (PLAN-041: pipeline reproducible de calidad)

- **Objetivo (Plan ID):** PLAN-041 (checks automatizados y entorno de verificación reproducible).
- **Contexto/insumos:** las suites ya estaban en verde, pero requerían exportar `PYTHONPATH`/`DATABASE_URL` a mano y no había un comando único ni CI; `npm test` quedaba en modo watch.
- **Acciones realizadas:**
  - **Scripts de verificación:** `scripts/verify.ps1` (Windows) y `scripts/verify.sh` (Linux/macOS/WSL) ejecutan backend pytest, frontend lint, typecheck, tests one-shot y build; opción `-SkipBuild`/`--skip-build`; fallan con código distinto de cero y mensaje del paso.
  - **Entorno determinista:** `backend/tests/conftest.py` fija `DATABASE_URL=sqlite:///:memory:` antes de importar la app, de modo que `pytest tests/api tests/core` funciona sin variables externas.
  - **Scripts npm:** `typecheck` (`tsc --noEmit`) y `test:run` (`vitest run`) para evitar watch mode en CI/scripts.
  - **Makefile:** `check-backend`, `check-frontend`, `check` (sin build) y `verify` (pipeline completo).
  - **CI:** `.github/workflows/ci.yml` con jobs backend (Python 3.11, pip cache, SQLite in-memory) y frontend (Node 20, `npm ci`, lint/typecheck/test/build) en push a `main` y PR.
  - **Docs:** `docs/CI.md` (comandos, pasos, alcance y troubleshooting) y README (quality gate + testing).
- **Archivos tocados:**
  - `scripts/verify.ps1`, `scripts/verify.sh`, `.github/workflows/ci.yml`, `docs/CI.md` (nuevos)
  - `backend/tests/conftest.py`, `frontend/package.json`, `Makefile`, `README.md`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `powershell -File scripts/verify.ps1 -SkipBuild` → **All checks passed**.
  - `powershell -File scripts/verify.ps1` (completo) → **All checks passed**: backend **162 passed**; frontend **54 passed**; `lint`/`typecheck`/`build` OK.
  - `bash -n scripts/verify.sh` → sintaxis OK (ejecución completa no realizada en Windows).
- **Hallazgos / riesgos / deuda:**
  - `npm run test -- --run` se quedó en watch mode en Windows; se sustituyó por `test:run` (`vitest run`) en scripts, Makefile y CI.
  - El workflow no se ha ejecutado aún en GitHub Actions (requiere push); validado localmente con los mismos comandos.
  - No se construyen imágenes Docker en CI; permanece como verificación manual (`make build`).
- **Decisiones:** ninguna nueva; DEC-004/010 aplicadas (sin red real; pipeline determinista).
- **Siguiente paso:** validación funcional de PLAN-021/PLAN-023 en entorno autorizado, code-splitting de PLAN-022 y observabilidad/runbooks (PLAN-040/042).

## 2026-11-13 — Backend/Security (PLAN-031: límites, CORS y secretos)

- **Objetivo (Plan ID):** PLAN-031 (cierre: límites de recursos, configuración CORS y manejo de secretos).
- **Contexto/insumos:** la validación de targets/puertos ya rechazaba formatos inválidos, pero un CIDR enorme o una lista completa de puertos podía encolar trabajo desproporcionado; CORS aceptaba cualquier valor y `SECRET_KEY` tenía un placeholder silencioso.
- **Acciones realizadas:**
  - **Límites de recursos:** `normalize_target` rechaza CIDR/rangos por encima de `MAX_HOSTS_PER_SCAN` (default `1024`) sin materializar hosts; `normalize_port_range` suma el total de puertos y rechaza por encima de `MAX_PORTS_PER_SCAN` (default `65535`). Ambos límites se leen de `Settings` en los schemas, así que aplican a scans y `scan_config` de schedules.
  - **Configuración:** `Settings` valida límites positivos, normaliza CORS y rechaza wildcard `*` o lista vacía; nuevo `uses_default_secret`; warning de arranque en `ENV=production` si sigue el placeholder.
  - **Capacidades:** revisión de `docker-compose.yml`/`docker-compose.dev.yml`: backend y celery solo con `NET_RAW`/`NET_ADMIN`, sin `privileged`; `beat` sin `cap_add`.
  - **Alineación UI:** `utils/validation.ts` replica el límite de 1024 hosts y acepta rangos IPv4 (`a-b`) con orden y tamaño validados.
  - **Docs:** contrato §3.1/§6 (límites, CORS, suites), README (security/config), `docs/DOCKER.md` (servicio `beat` y capacidades), `.env.example`/`.env.docker` (`MAX_HOSTS_PER_SCAN`).
- **Archivos tocados:**
  - `backend/app/core/validation.py`, `backend/app/config.py`, `backend/app/schemas/scan.py`, `backend/app/main.py`
  - `backend/tests/core/test_validation.py`, `backend/tests/core/test_config.py` (nuevo), `backend/tests/api/test_input_validation.py`
  - `frontend/src/utils/validation.ts`, `frontend/src/utils/validation.test.ts`
  - `docs/CONTRACT.md`, `docs/DOCKER.md`, `README.md`, `.env.docker`, `backend/.env.example`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `pytest tests/core/test_validation.py tests/core/test_config.py tests/api/test_input_validation.py` → **80 passed**.
  - `pytest tests/api tests/core` → **162 passed**.
  - `npx vitest run` → **54 passed**; `npm run lint` → OK; `npx tsc --noEmit` → OK; `npm run build` → OK (aviso de bundle ~530 kB).
  - Sin escaneos ni DNS reales; límites verificados con tests deterministas (DEC-004/010).
- **Hallazgos / riesgos / deuda:**
  - El límite de hosts se valida sintácticamente; un hostname puede resolver a múltiples IPs fuera del recuento (no se resuelve DNS).
  - La UI ahora rechaza `/8` y rangos grandes: coherente con backend, pero puede sorprender a quien esperaba truncado; documentado en contrato/README.
  - Queda pendiente el pipeline reproducible (PLAN-041) y la validación funcional/E2E en entorno autorizado.
- **Decisiones:** ninguna nueva; DEC-003/004/010 vigentes (capacidades mínimas y alcance autorizado).
- **Siguiente paso:** PLAN-041 (pipeline lint/type/build/tests reproducible) y luego validación funcional de PLAN-021/PLAN-023.

## 2026-11-12 — Backend/Security (PLAN-031: validación estricta de entradas)

- **Objetivo (Plan ID):** PLAN-031 (slice de validación de targets/puertos/config).
- **Contexto/insumos:** `ScanCreate` solo comprobaba target no vacío y `port_range` se limitaba a `strip()`; `scan_config` de schedules se validaba recién en el despacho. El motor ya soportaba IP/CIDR/rango/hostname.
- **Acciones realizadas:**
  - **TDD núcleo:** `tests/core/test_validation.py` en rojo y luego `app/core/validation.py`: `normalize_target` (IPv4/IPv6, CIDR, rango IPv4 con misma familia y orden, hostname sintáctico sin DNS), `normalize_port_range` (listas/rangos, 1–65535, orden, tokens vacíos) y `normalize_scan_config` (target/puertos/`scan_type`, preserva claves extra). **40 pruebas**.
  - **Schemas:** `ScanCreate` usa los normalizadores (target/rango); `ScheduleCreate` y `ScheduleUpdate` validan y normalizan `scan_config`.
  - **API:** nuevo `tests/api/test_input_validation.py` (**22 pruebas**): `422` para targets/puertos/config inválidos, aceptación de IPv4/hostname con guion/IPv6/rango IPv4 y normalización de espacios.
  - **Contrato:** §3.1 documenta formatos aceptados, límites y rechazo `422`; §6 añade las nuevas suites.
- **Archivos tocados:**
  - `backend/app/core/validation.py` (nuevo)
  - `backend/app/schemas/scan.py`
  - `backend/tests/core/test_validation.py`, `backend/tests/api/test_input_validation.py` (nuevos)
  - `docs/CONTRACT.md`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `pytest tests/core/test_validation.py` → **40 passed**.
  - `pytest tests/api/test_input_validation.py` → **22 passed**.
  - `pytest tests/api tests/core` → **144 passed** (39 s).
  - Sin escaneos ni resoluciones DNS reales (validación sintáctica), conforme a DEC-004.
- **Hallazgos / riesgos / deuda:**
  - La UI todavía no ofrece rangos IPv4 (`a-b`) aunque la API los acepta; documentado para alinear en PLAN-021/031.
  - Faltan por endurecer límites de recursos (p. ej. tamaño máximo de CIDR/rango, concurrencia), revisión de CORS/capacidades y chequeo de secretos.
  - `name`/`description` de schedules no tienen límite explícito en `ScheduleUpdate`.
- **Decisiones:** ninguna nueva; DEC-004/010 vigentes.
- **Siguiente paso:** completar PLAN-031 (límites, CORS/capacidades, secretos), alinear validación de rangos en UI y continuar con PLAN-041.

## 2026-11-12 — Frontend (PLAN-022: navegador de resultados, filtros y export)

- **Objetivo (Plan ID):** PLAN-022 (resultados, filtros, visualización y export en UI).
- **Contexto/insumos:** `/results` era “Coming Soon”; el backend ya expone `GET /api/scans/{id}` con `results/ports` y `POST /api/scans/{id}/export` (`json`/`csv`/`xml`, cubierto por contrato).
- **Acciones realizadas:**
  - **TDD utilidades:** `utils/results.test.ts` primero en rojo (módulo inexistente) y luego `utils/results.ts`: aplanado `ScanResult[]`→filas por puerto, filtros combinables (texto, estado, protocolo, servicio), opciones únicas ordenadas, conteo de hosts y nombre de export determinista (`scan-<id>-<YYYYMMDD>.<fmt>`). **11 pruebas**.
  - **Pantalla `/results`:** selector de scan (preselecciona el último completado con puertos), tabla host/puerto con chips de estado, búsqueda libre y filtros por estado/protocolo/servicio, contadores `HOSTS`/`PORTS`, limpieza de filtros y estados de carga/vacío/error; aviso si el scan sigue activo.
  - **Export:** botones JSON/CSV/XML que descargan el blob de la API con nombre determinista y manejo de error; deshabilitados sin resultados.
  - **Navegación:** ruta real en `App.tsx` y botón “Results” en la cabecera del Dashboard.
  - **Docs:** flujo y cobertura actualizados en `docs/UI.md`.
- **Archivos tocados:**
  - `frontend/src/utils/results.ts`, `frontend/src/utils/results.test.ts` (nuevos)
  - `frontend/src/components/Results/ResultsBrowser.tsx` (nuevo)
  - `frontend/src/App.tsx`, `frontend/src/components/Dashboard/Dashboard.tsx`
  - `docs/UI.md`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `npx vitest run src/utils/results.test.ts` → **11 passed** (tras rojo inicial).
  - `npm run lint` → **OK (0 warnings)**.
  - `npx tsc --noEmit` → **OK** (corregidos literales de `PortState` en tests).
  - `npx vitest run` → **52 passed** (6 archivos).
  - `npm run build` → **OK**; aviso de chunk principal ~529 kB (deuda de code-splitting).
  - Backend sin cambios en esta iteración (última suite: 82 passed).
- **Hallazgos / riesgos / deuda:**
  - No hay pruebas de componentes DOM (jsdom/testing-library no instalados); la lógica se cubre con utilidades puras y el render se validó vía `tsc`/build.
  - Export probado a nivel de contrato backend y de nombre/descarga en UI, sin e2e real.
  - El bundle principal creció; considerar `React.lazy`/`manualChunks`.
- **Decisiones:** ninguna nueva; DEC-006/008/009/010 vigentes.
- **Siguiente paso:** validación funcional de PLAN-021 y de `/results` con backend real en entorno controlado; luego PLAN-031 (hardening) y PLAN-041 (pipeline).

## 2026-11-11 — Frontend (PLAN-023 fase 3: UI de schedules)

- **Objetivo (Plan ID):** PLAN-023 fase 3 (cerrar flujo de schedules en UI).
- **Contexto/insumos:** `/schedules` era “Coming Soon”; API/CRUD, `next_run_at` y despachador ya implementados (fase 1+2); guardrail de DEC-008 vigente hasta esta fase.
- **Acciones realizadas:**
  - **Utilidades puras:** `utils/schedule.ts` — validación de cron de 5 campos (rangos, listas, pasos, nombres de campo), formateo de timestamps UTC sin desfase local, resumen seguro de `scan_config`, mapeo `Schedule`↔formulario y `validateScheduleForm` reutilizando validaciones de target/puertos.
  - **Diálogo:** `ScheduleDialog` con nombre/descripción, target, tipo de scan, puertos, expresión cron + presets, opciones y `enabled`; errores por campo y aviso de autorización para escaneos desatendidos.
  - **Pantalla:** `/schedules` con tabla de configuración/cron/estado/última y próxima ejecución/contadores; crear, editar, habilitar/deshabilitar con actualización optimista y borrado con diálogo de confirmación; estados de carga/vacío/error y estética consola cyan.
  - **Navegación:** ruta real en `App.tsx` y botón “Schedules” en la cabecera del Dashboard.
  - **Tests:** `utils/schedule.test.ts` (11 pruebas) para cron, formato UTC, resumen de config, mapeo de formulario y validación.
- **Archivos tocados:**
  - `frontend/src/utils/schedule.ts`, `frontend/src/utils/schedule.test.ts` (nuevos)
  - `frontend/src/components/Schedules/Schedules.tsx`, `ScheduleDialog.tsx` (nuevos)
  - `frontend/src/App.tsx`, `frontend/src/components/Dashboard/Dashboard.tsx`
  - `docs/UI.md`, `docs/CONTRACT.md`, `decisions.md`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `npm run lint` → **OK (0 warnings)**.
  - `npx tsc --noEmit` → **OK**.
  - `npx vitest run` → **41 passed** (5 archivos; schedules 11).
  - `npm run build` → **OK** (aviso de chunk >500 kB, deuda de code-splitting).
  - Backend sin cambios: `pytest tests/api tests/core` → **82 passed**.
  - Sin validación funcional contra backend/Beat reales (DEC-004).
- **Hallazgos / riesgos / deuda:**
  - La UI muestra horas en UTC de forma explícita; el backend serializa datetimes naive.
  - El bundle principal supera 500 kB tras añadir la vista; considerar `manualChunks`/lazy routes.
  - Falta prueba funcional del flujo de schedules con backend real y disparo de Beat en entorno autorizado.
- **Decisiones:** DEC-008 completada en sus tres fases; sin nuevas decisiones.
- **Siguiente paso:** validación funcional de PLAN-021 y de schedules en entorno controlado; luego PLAN-022 (resultados/filtros/export) y PLAN-031/041.

## 2026-11-11 — Backend/Infra (PLAN-023 fase 1+2: despachador de schedules)

- **Objetivo (Plan ID):** PLAN-023 fase 1 (despachador + tests) y fase 2 (Beat en Docker).
- **Contexto/insumos:** `Schedule` tenía CRUD pero sin motor de disparo; DEC-008 accepted (DB como fuente de verdad, idempotencia); `celery` no instalado localmente (fallback de test) y `croniter` ausente.
- **Acciones realizadas:**
  - **Núcleo:** `app/core/scheduler.py` con `compute_next_run` (`croniter`, UTC naive), `_scan_from_schedule` (mapea `scan_config` y valida `target`/`scan_type`), `_claim_schedule` (UPDATE condicional por `next_run_at` + `enabled`), `_increment_failed` y `dispatch_due_schedules` (selección de vencidos, avance de `next_run_at`, contadores, deshabilitado de cron inválido, scan `FAILED` si el enqueue falla, aislamiento de errores por schedule).
  - **Celery:** `dispatch_due_schedules_task` en `app/tasks.py` y `beat_schedule` cada 60 s en `app/celery_app.py`; fallback `_DummyCeleryApp.task` ahora acepta decoración directa (`@app.task`) como Celery.
  - **API/DB:** `ScheduleCreate`/`ScheduleUpdate` validan cron con `croniter`; `POST` calcula `next_run_at` si `enabled`; `PATCH` lo recalcula al cambiar cron/reactivar y lo limpia al deshabilitar.
  - **Infra:** servicios `beat` en `docker-compose.yml` y `docker-compose.dev.yml` con `celery beat` y **sin** `cap_add` (solo encola, no escanea); `croniter>=2.0.0` en `requirements.txt`.
  - **Contrato/docs:** sección 3.5 Schedules en `docs/CONTRACT.md` (CRUD, semántica de `next_run_at`, despacho asíncrono y validaciones); DEC-008 con fases 1–2 marcadas completadas.
- **Archivos tocados:**
  - `backend/app/core/scheduler.py` (nuevo)
  - `backend/app/tasks.py`, `backend/app/celery_app.py`
  - `backend/app/api/schedules.py`, `backend/app/schemas/scan.py`
  - `backend/tests/core/test_scheduler.py`, `backend/tests/core/test_dispatch_task.py` (nuevos)
  - `backend/tests/api/test_schedules_contract.py` (nuevo)
  - `backend/requirements.txt`
  - `docker-compose.yml`, `docker-compose.dev.yml`
  - `docs/CONTRACT.md`, `decisions.md`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `pytest tests/api tests/core` → **82 passed** (37.9 s): 12 scheduler + 10 contrato de schedules + 2 task de despacho + suite previa.
  - `croniter` 7.0.0 instalado y validado manualmente (`*/5 * * * *` → +5 min).
  - Sin ejecución real de Celery/Redis/Beat ni escaneos de red (DEC-004).
- **Hallazgos / riesgos / deuda:**
  - La idempotencia se apoya en `UPDATE ... WHERE next_run_at = leído`; con múltiples Beat el diseño evita dobles disparos, pero conviene ejecutar un solo Beat por despliegue.
  - Fechas naive UTC (`datetime.utcnow`) mantienen consistencia con el modelo actual; migrar a timezone-aware requiere decisión/migración global.
  - Pendiente fase 3: UI de schedules; el guardrail de DEC-008 sigue vigente (la UI actual no debe prometer ejecución automática).
  - Sin prueba de integración con broker real.
- **Decisiones:** DEC-008 (fases 1–2 implementadas); sin nuevas decisiones.
- **Siguiente paso:** UI de schedules (PLAN-023 fase 3), validación funcional de PLAN-021 y luego PLAN-022/031/041.

## 2026-11-11 — Frontend/UX (cierre PLAN-020, avance PLAN-021, DEC-008)

- **Objetivo (Plan ID):** PLAN-020 (cierre), PLAN-021 (avance), DEC-008 (decisión).
- **Contexto/insumos:** tema base aplicado solo en Dashboard; `ScanDetails`/`ScanDialog` sin identidad visual; sin configuración ESLint; validación de formulario inexistente; DEC-008 pendiente.
- **Acciones realizadas:**
  - **Tema y guía visual:** extraído el tema a `frontend/src/theme.ts` (`createAppTheme`, tokens cyan/fondos/tipografía, overrides de Paper/Card/Button/Chip/Inputs/Progress/Table/Alert/Accordion/Dialog/Snackbar); `main.tsx` consume `appTheme`; creada `docs/UI.md` con tokens, componentes, semántica de estados, patrones de pantalla y accesibilidad (verificación DEC-009).
  - **Utilidades con TDD:** `utils/scan.ts` (estados activos/terminales, colores de estado y puerto, duración, mapeo WS→Scan), `utils/validation.ts` (target IPv4/IPv6/CIDR/hostname y rangos de puertos) y `utils/errors.ts` (mensajes de error Axios/JS). 24 pruebas nuevas.
  - **Dashboard:** cards reutilizables y estilizadas, cabeceras de sección `> ACTIVE_OPERATIONS`/`> RECENT_OPERATIONS`, estado vacío de consola; refactor de `loadScans` con `useCallback`, WS sobre `activeScansRef` y `snapshotToScanUpdates` (sin `any`).
  - **Detalle:** cabecera `> SCAN_DETAILS`, panel de resumen, progreso en vivo, alertas de `error_message`, tabla con chips semánticos, contador de hosts y **cancelación** de scans activos (`PATCH status=cancelled`). Efectos/WS refactorizados con `useCallback`/refs para evitar bucles y warnings.
  - **Diálogo:** validación local con `validateScanForm` (errores por campo, helperText, bloqueo de envío inválido), aviso de autorización, opciones agrupadas y estados de carga/error.
  - **ESLint:** creada `.eslintrc.cjs` (eslint recommended + TS + react-hooks, `react-refresh` off, `no-explicit-any` error) y corregidos los hallazgos hasta dejar `npm run lint` limpio.
  - **DEC-008:** aceptada estrategia **Celery Beat + despachador periódico DB idempotente** (fases y guardrails documentados), desbloqueando PLAN-023.
- **Archivos tocados:**
  - `frontend/src/theme.ts` (nuevo)
  - `frontend/src/main.tsx`
  - `frontend/src/types/index.ts`
  - `frontend/src/utils/scan.ts`, `errors.ts`, `validation.ts` (nuevos) + `*.test.ts`
  - `frontend/src/components/Dashboard/Dashboard.tsx`
  - `frontend/src/components/ScanDetails/ScanDetails.tsx`
  - `frontend/src/components/ScanDialog.tsx`
  - `frontend/src/services/websocket.test.ts`
  - `frontend/.eslintrc.cjs` (nuevo)
  - `docs/UI.md` (nuevo)
  - `decisions.md`, `plan.md`, `bitacora.md`
- **Verificación:**
  - `npm run lint` → **OK (0 warnings)**.
  - `npx tsc --noEmit` → **OK**.
  - `npm run build` → **OK** (vite, 11.590 módulos).
  - `npx vitest run` → **30 passed** (4 archivos: WS 6, scan 9, errores 4, validación 11).
  - Backend sin cambios en esta iteración; última ejecución `pytest tests/api tests/core` → 58 passed.
  - Sin validación funcional/e2e del flujo UI contra backend real.
- **Hallazgos / riesgos / deuda:**
  - No hay pruebas de componentes DOM (jsdom/testing-library no instalados); la lógica de UI se cubre vía utilidades puras.
  - `PLAN-021` requiere validación funcional/e2e; `PLAN-023` requiere implementación del despachador + `croniter` + servicio Beat.
  - Accesibilidad validada de forma básica (contraste/chips con texto); falta auditoría formal.
- **Decisiones:** **DEC-008 accepted**; DEC-009 verificada con guía visual; DEC-006/007/010 vigentes.
- **Siguiente paso:** implementar PLAN-023 fase 1 (despachador `dispatch_due_schedules` + tests con reloj mockeado) y completar PLAN-021 con validación funcional; luego PLAN-022 (export/tablas) y PLAN-031/041.

## 2026-11-11 — Full-stack/QA (cierre PLAN-011: contrato v1.0)

- **Objetivo (Plan ID):** PLAN-011 (cierre) + alineación de cliente dentro de PLAN-020.
- **Contexto/insumos:** DEC-006 aceptada; tests WS inestables por bloqueo; necesidad de formalizar contrato compartido y ampliar cobertura.
- **Acciones realizadas:**
  - **Backend/WS:** extraídos builders puros `scan_snapshot`, `build_status_message`, `build_update_message`, `build_error_message` y constante `TERMINAL_STATUSES`; el endpoint ahora cierra explícitamente el socket tras emitir el estado terminal, lo que eliminó el bloqueo de los tests WS.
  - **Contrato compartido:** creado `docs/CONTRACT.md` v1.0 (enums, entidades, endpoints REST, ciclo de vida/cancelación, export, protocolo WS, heartbeat ping/pong, reglas de cliente y mapa schema↔tipo).
  - **Pruebas TDD:** ampliado `backend/tests/api/test_scan_contract.py` con `TestScanContract` (filtros, paginación, validaciones, export json/csv/xml, 404/422), `TestSchemaContract` (resumen vs detalle, defaults/validación) y `TestWebSocketMessageBuilders` (campos exactos); `TestWebSocketContract` verifica `error` y cierre post-`status` terminal.
  - **Frontend:** `types/index.ts` añade `ScanSummary`, `ScanSnapshotMessage`, `ScanErrorMessage` y `ScanWSMessage`; `services/websocket.ts` tipado, ignora `pong`, no reconecta en cierre intencional ni en estado terminal y limpia el ping de forma centralizada.
  - **Frontend/test tooling:** `npm ci` instala dependencias; `vite.config.ts` incorpora configuración `vitest`; `services/websocket.test.ts` añade 6 pruebas con `WebSocket` mockeado y timers falsos; eliminados imports sin uso en `ScanDetails` que rompían `tsc`.
- **Archivos tocados:**
  - `backend/app/api/websocket.py`
  - `backend/tests/api/test_scan_contract.py`
  - `frontend/src/types/index.ts`
  - `frontend/src/services/websocket.ts`
  - `frontend/src/services/websocket.test.ts` (nuevo)
  - `frontend/src/components/ScanDetails/ScanDetails.tsx`
  - `frontend/vite.config.ts`
  - `docs/CONTRACT.md` (nuevo)
  - `plan.md`
  - `bitacora.md`
- **Verificación:**
  - `python -m pytest tests/api/test_scan_contract.py -q` → **25 passed**.
  - `python -m pytest tests/api tests/core -q` → **58 passed, 0 failed, exit 0** (25 contrato + 5 lifecycle + 28 core).
  - Warnings no bloqueantes (deprecaciones Pydantic/FastAPI/SQLAlchemy/`utcnow`, `CallSpec2`).
  - `npx tsc --noEmit` → **OK**; `npm run build` → **OK** (vite, 11.586 módulos).
  - `npx vitest run` → **6 passed** (1 archivo).
  - `npm run lint` → **no ejecutable**: no existe configuración ESLint en el proyecto.
  - Sin validación E2E de red/WS en entorno autorizado (DEC-004).
- **Hallazgos / riesgos / deuda:**
  - El contrato v1.0 es baseline: sin versionado formal de payloads ni broadcast pub/sub (mejora futura).
  - Transición en vivo `running → terminal` dentro del loop WS está cubierta por builders + E2E pendiente, no por test con socket concurrente (limitación de SQLite in-memory/TestClient).
  - Persisten deudas: configuración ESLint ausente, propagación completa del tema cyberpunk cyan, DEC-008 (schedules), deprecaciones Pydantic v2/`lifespan`/`declarative_base`/`utcnow`.
- **Decisiones:** DEC-006 vigente (baseline ya formalizado en `docs/CONTRACT.md`); sin nuevas decisiones.
- **Siguiente paso:** PLAN-020 (tema cyberpunk cyan en vistas restantes + `vitest`), PLAN-021 (flujo UI), PLAN-023/DEC-008 y PLAN-031/041 (hardening/CI).

## 2026-11-11 — Full-stack (continuación PLAN-011)
- **Objetivo (Plan ID):** PLAN-011 (en progreso).
- **Contexto/insumos:** DEC-006 (baseline), necesidad de separar contratos de listado/detalle, alinear frontend a payload WS y ampliar pruebas de contrato con mocks/fixtures.
- **Acciones realizadas:**
  - **Backend/schemas:** añadido `ScanSummaryResponse` y refactorizado `ScanResponse` (detalle con `results`); exportado en `schemas/__init__` y aplicado en `GET /api/scans` (listado sin resultados pesados) manteniendo detalle en `GET /api/scans/{id}`.
  - **Backend/WS:** mejorada testabilidad/robustez del endpoint (`/ws/scan/{id}`) con short-circuit para scans en estado terminal y payload contractual consistente (`status/update/error`, `ports_found`, `error_message`).
  - **Frontend:** actualizado `types/index.ts` (`results` opcional) y normalización de eventos WS en `Dashboard` y `ScanDetails` (mapeo `ports_found`→`total_ports_found`, manejo de eventos `error` y actualización de estado).
  - **Pruebas TDD:** añadido `backend/tests/api/test_scan_contract.py` con contratos HTTP (listado resumen sin `results`, detalle con `results/ports`) y casos WS de contrato (error not-found y estado terminal) basados en DB/SessionLocal mockeada.
- **Archivos tocados:**
  - `backend/app/schemas/scan.py`
  - `backend/app/schemas/__init__.py`
  - `backend/app/api/scans.py`
  - `backend/app/api/websocket.py`
  - `frontend/src/types/index.ts`
  - `frontend/src/components/Dashboard/Dashboard.tsx`
  - `frontend/src/components/ScanDetails/ScanDetails.tsx`
  - `backend/tests/api/test_scan_contract.py` (nuevo)
  - `plan.md`
  - `bitacora.md`
- **Verificación:**
  - `python -m pytest tests/api/test_scan_contract.py::TestScanContract -q` (desde `backend/`, `PYTHONPATH=.`, `DATABASE_URL=sqlite:///:memory:`) → **2 passed**.
  - `python -m pytest tests/api tests/core -q` → **35 passed, 0 failed, exit 0**.
  - Ejecución de tests WS del archivo de contrato quedó pendiente de estabilización en este entorno (bloqueo/timeout observado al correr la clase WS); requieren ajuste adicional de harness/entorno para ejecución determinista.
  - Sin validación E2E de red/WS en entorno autorizado; sin build frontend en este entorno.
- **Hallazgos / riesgos / deuda:**
  - Contrato compartido aún no formalizado como artefacto único (tipos/OpenAPI/event schema versionado) entre backend y frontend.
  - Cobertura de contrato WS/API incompleta (falta suite estable y casos de transición/progreso en vivo).
  - Persisten deprecaciones (Pydantic v2, FastAPI lifespan, SQLAlchemy `declarative_base`/`utcnow`) y warnings de entorno.
- **Decisiones:** DEC-006 sigue aceptada (baseline); sin nuevas decisiones formales.
- **Siguiente paso:** estabilizar y ampliar tests de contrato WS/API (transiciones, errores, terminales), formalizar tipado/esquema compartido y continuar PLAN-020/021 con pruebas `vitest` y propagación del tema cyberpunk cyan.

## 2026-11-11 — Full-stack (avance PLAN-011, cierre PLAN-012, avance PLAN-020)
- **Objetivo (Plan ID):** PLAN-011 (en progreso), PLAN-012 (done), PLAN-020 (en progreso).
- **Contexto/insumos:** contrato y ciclo de vida identificados en PLAN-002; DEC-006/007/009/010; solicitud de continuar con PLAN-011/012/020; entorno sin `celery`/tooling frontend completo para build TS.
- **Acciones realizadas:**
  - **Backend (PLAN-012/011):** normalizada cancelación en `PATCH /api/scans/{id}` (revoca tarea si activa, persiste `cancelled`, `completed_at`, `error_message`) y en `DELETE` (revoca si `pending/running` antes de eliminar). Robustecido `WS /ws/scan/{id}`: manejo de scan inexistente (`type:error` + cierre), payload consistente con `ports_found` y `error_message`, y polling/comparación de estado mejorados.
  - **Testabilidad:** añadidos fallbacks sin dependencia dura de Celery en `app/celery_app.py` y `app/tasks.py` para permitir ejecución de pruebas en entornos sin Celery.
  - **Pruebas TDD:** creado `backend/tests/api/test_scans_lifecycle.py` (5 tests: creación/enqueue mockeado, cancelación por PATCH, delete con revoke en running/pending, 404) usando SQLite in-memory, overrides de DB y mocks de Celery.
  - **Frontend (PLAN-020/DEC-009):** aplicado tema base "consola cyberpunk cyan" en `frontend/src/main.tsx` (paleta, tipografía monoespaciada, overrides MUI, fondo/grid/glow) y ajustes visuales iniciales en `Dashboard`.
  - **Decisiones/plan:** `DEC-006` aceptada (baseline de contrato tiempo real/lifecycle). `plan.md` actualizado (estados, próximos pasos, historial).
- **Archivos tocados:**
  - `backend/app/api/scans.py`
  - `backend/app/api/websocket.py`
  - `backend/app/celery_app.py`
  - `backend/app/tasks.py`
  - `backend/tests/api/__init__.py` (nuevo)
  - `backend/tests/api/test_scans_lifecycle.py` (nuevo)
  - `frontend/src/main.tsx`
  - `frontend/src/components/Dashboard/Dashboard.tsx`
  - `decisions.md`
  - `plan.md`
  - `bitacora.md`
- **Verificación:**
  - Backend: `python -m pytest tests/api tests/core -q` (desde `backend/`, `PYTHONPATH=.`, `DATABASE_URL=sqlite:///:memory:`) → **33 passed, 0 failed, exit 0** (warnings no bloqueantes de deprecación/deps).
  - Frontend: intento de verificación TypeScript (`tsc`/bin local) no disponible en entorno actual → **build/typecheck no ejecutado**.
  - No se realizaron escaneos reales ni validaciones E2E de red/WS en entorno autorizado.
- **Hallazgos / riesgos / deuda:**
  - PLAN-011 pendiente de refinamiento: contratos/schemas de listado vs detalle, tipado compartido formal, suite de contrato WS/API ampliada y alineación completa cliente-servidor.
  - PLAN-020 pendiente: propagar tema a todas las vistas/componentes, alinear manejo de eventos/errores WS en UI y añadir pruebas `vitest` con mocks.
  - Persisten deudas: `DEC-008` (schedules sin motor), progreso fino de puertos, deprecaciones (Pydantic v1 validators/config, `on_event`, `declarative_base`, `utcnow`), y cobertura fuera de core/api-lifecycle.
  - Tests API dependen de estrategia de import/test DB; mantener aislamiento por fixtures/mocks.
- **Decisiones:** DEC-006 aceptada (baseline). DEC-007/009/010 vigentes. DEC-008 propuesta.
- **Siguiente paso:** continuar **PLAN-011** (contrato/schemas/tests de contrato y tipos), **PLAN-020** (propagación UI cyberpunk cyan + alineación WS/errores + tests vitest) y preparar **PLAN-021/023**; resolver deprecaciones y ampliar cobertura bajo TDD.

## 2026-11-11 — Backend/QA/Orchestrator (cierre PLAN-010 y PLAN-030)
- **Objetivo (Plan ID):** PLAN-010 (done), PLAN-030 (done).
- **Contexto/insumos:** solicitud de cierre de tareas en proceso; requisitos previos de TDD/mocks-fixtures (DEC-010) y corrección P0 en core; disponibilidad de `pip/pytest` en entorno.
- **Acciones realizadas:**
  - Instaladas dependencias de test en entorno (`pytest`, `pytest-asyncio`) y configurado `asyncio_default_fixture_loop_scope` en `backend/pyproject.toml`.
  - Ampliada la suite core con mocks/fixtures: `tests/core/test_port_scanner.py`, `tests/core/test_network_mapper.py`, `tests/core/test_service_detector.py`, `tests/core/test_os_fingerprint.py`; ajustados tests existentes (`test_scanner.py`) y corregidos casos para reflejar contratos reales (mock de `socket`, semántica de extracción de versión SSH, fake `nmap` compatible).
  - Formalizada semántica baseline de ejecución/métricas y cerrado **DEC-007 (accepted)** (comprehensive tcp+udp baseline, protocolo preservado, heurística UDP y métricas actuales documentadas).
  - Actualizado `plan.md`: `PLAN-010` y `PLAN-030` marcados `done`, próximo slice reorientado a `PLAN-011/012/020`, historial actualizado.
- **Archivos tocados:**
  - `backend/pyproject.toml`
  - `backend/tests/core/test_scanner.py`
  - `backend/tests/core/test_port_scanner.py` (nuevo)
  - `backend/tests/core/test_network_mapper.py` (nuevo)
  - `backend/tests/core/test_service_detector.py` (nuevo)
  - `backend/tests/core/test_os_fingerprint.py` (nuevo)
  - `plan.md`
  - `decisions.md`
  - `bitacora.md`
- **Verificación:**
  - `python -m pip install pytest pytest-asyncio` → instalación exitosa.
  - `python -m pytest tests/core -q` (desde `backend/`, `PYTHONPATH=.`, `DATABASE_URL=sqlite:///:memory:`) → **28 passed, 0 failed, exit 0** (2 warnings no bloqueantes: `anyio` CallSpec2 y `declarative_base` deprecado en SQLAlchemy 2.0).
  - No se ejecutaron escaneos reales ni pruebas de integración de red (DEC-004).
- **Hallazgos / riesgos / deuda:**
  - Cobertura de core establecida; falta expandir a `tasks`, `api`, `schemas/models`, `websocket`, integración DB/Celery mockeada y frontend (`vitest`) según TDD transversal.
  - Deudas abiertas: contrato/progreso/WS (DEC-006), refinamiento de semántica/progreso fino y opciones no aplicadas (seguimiento en PLAN-011/012/031), schedules sin ejecución (DEC-008), warnings de dependencias.
  - Importar `app` puede acarrear efectos de inicialización (DB/config); mantener aislamiento en futuros tests.
- **Decisiones:** DEC-007 aceptada; DEC-006/DEC-008 permanecen `proposed`; DEC-009/DEC-010 vigentes.
- **Siguiente paso:** iniciar **PLAN-011** (contrato canónico API/WS/schemas + tests de contrato), **PLAN-012** (ciclo de vida/cancelación coherente) y **PLAN-020** (alineación frontend + base visual cyberpunk cyan, DEC-009) con enfoque TDD.

## 2026-11-11 — Backend/QA/Orchestrator (TDD, harness y pruebas core)
- **Objetivo (Plan ID):** PLAN-030 (en progreso), PLAN-010 (en progreso), incorporación de requisito "TDD con mocks y fixtures".
- **Contexto/insumos:** solicitud explícita de cubrir todo con TDD usando mocks/fixtures; fix P0 previo en `backend/app/core/scanner.py`; ausencia de suite de pruebas backend activa.
- **Acciones realizadas:**
  - Incorporado TDD como práctica obligatoria y estrategia de pruebas con mocks/fixtures en `agents.md`, `plan.md` (principios, PLAN-030 en `doing`, DoD de programa, próximo slice) y `decisions.md` (**DEC-010 accepted**).
  - Creado harness de pruebas backend: `backend/tests/{__init__,conftest}.py`, `backend/tests/core/{__init__,test_scanner}.py` con fixtures/mocks (`AsyncMock`/`Mock`) para aislar red, descubrimiento, puertos, servicios y OS.
  - Añadidas pruebas unitarias para `NetworkScanner` cubriendo: modo `COMPREHENSIVE` (uso de `DEFAULT_UDP_PORTS`, preservación de protocolo tcp/udp, mismo puerto en ambos protocolos), etiquetado de protocolo en `TCP_CONNECT`/`UDP`, y caso sin hosts activos.
- **Archivos tocados:**
  - `agents.md` (actualizado: TDD obligatorio, matriz de verificación y DoD)
  - `plan.md` (actualizado: principios TDD/mocks-fixtures, PLAN-030 doing, próximos pasos y DoD)
  - `decisions.md` (actualizado: DEC-010 accepted)
  - `backend/tests/conftest.py` (nuevo)
  - `backend/tests/__init__.py`, `backend/tests/core/__init__.py` (nuevos)
  - `backend/tests/core/test_scanner.py` (nuevo)
  - `bitacora.md` (actualizado: esta entrada)
- **Verificación:**
  - `python -m pytest tests/core/test_scanner.py -q` (desde `backend/`) → **no ejecutado por entorno**: `pytest` no está instalado (`No module named pytest`, exit 1).
  - Verificación de sanidad equivalente con mocks (sin red): script temporal ejecutado con `PYTHONPATH=. DATABASE_URL=sqlite:///:memory:` desde `backend/` → **`SANITY_OK` (exit 0)**, confirmando el comportamiento corregido del scanner (comprehensive tcp/udp, protocolo preservado, uso de `DEFAULT_UDP_PORTS`). Nota: aparecieron warnings de import/async-mock no críticos durante la ejecución.
  - No se ejecutaron escaneos reales (DEC-004).
- **Hallazgos / riesgos / deuda:**
  - Entorno local sin dependencias de test (`pytest`/`pytest-asyncio`) instaladas; se requiere instalarlas (p.ej. extras dev) para correr la suite formalmente.
  - Cadena de imports de `app` dispara inicialización de DB/config; los tests/harness deberán mantener aislamiento (env/fixtures/mocks) para ser deterministas en distintos entornos.
  - Cobertura aún inicial: faltan tests para `port_scanner`, `service_detector`, `os_fingerprint`, `network_mapper`, `tasks`, API/WS/schemas, frontend (Vitest) y contratos; PLAN-010 requiere más casos y validación controlada.
- **Decisiones:** DEC-010 aceptada. DEC-006/007/008 siguen `proposed`.
- **Siguiente paso:** instalar dependencias de desarrollo y ejecutar `pytest` formalmente; ampliar suite TDD (mocks/fixtures) para cerrar criterios de PLAN-010 y continuar con PLAN-030/PLAN-011 (contrato canónico y tests de contrato).

## 2026-11-11 — Backend/Orchestrator (PLAN-010 inicio + dirección UI)
- **Objetivo (Plan ID):** PLAN-010 (en progreso), actualización de roadmap y captura de requisito de diseño.
- **Contexto/insumos:** hallazgos P0 de PLAN-002 (`core/scanner.py`), solicitud de look & feel "consola cyberpunk cyan", `plan.md` y `decisions.md`.
- **Acciones realizadas:**
  - Corregido P0 en `backend/app/core/scanner.py`: definida lista base `DEFAULT_UDP_PORTS` para modo `COMPREHENSIVE` (elimina referencia a `udp_common` no definido), preservado protocolo por origen (`tcp`/`udp`) al procesar resultados y ajustada la construcción de hallazgos/servicios por protocolo.
  - Actualizado `plan.md`: añadida dirección de diseño UI "consola cyberpunk cyan" como principio transversal y estado de `PLAN-010` a `doing`.
  - Registrada `DEC-009` (accepted) en `decisions.md` para la dirección visual.
- **Archivos tocados:**
  - `backend/app/core/scanner.py`
  - `plan.md`
  - `decisions.md`
  - `bitacora.md`
- **Verificación:**
  - `python -m py_compile backend/app/core/scanner.py` → `PY_COMPILE_EXIT=0` (compilación/sintaxis OK).
  - No se ejecutaron tests automatizados ni escaneos reales en esta iteración; pendiente validar comportamiento funcional/semántica UDP y casos `COMPREHENSIVE` en entorno autorizado (parte restante de PLAN-010, ligado a DEC-007).
- **Hallazgos / riesgos / deuda:**
  - Semántica UDP (timeouts como `OPEN` en `port_scanner`) y definición formal de métricas/progreso siguen abiertas (DEC-007).
  - Contrato/progreso fino y estrategia WS pendientes (DEC-006, PLAN-011/012); `schedules` sin motor de ejecución (DEC-008).
  - Cambio funcional no cubierto aún por pruebas de regresión.
- **Decisiones:** DEC-009 aceptada. DEC-006/007/008 permanecen `proposed`.
- **Siguiente paso:** completar PLAN-010 con pruebas dirigidas/validación controlada y definición de semántica (DEC-007), luego avanzar PLAN-011 con borrador de contrato canónico API/WS/schemas y su alineación.

## 2026-11-11 — Orchestrator (plan de profesionalización)
- **Objetivo (Plan ID):** Evolución de roadmap hacia nivel profesional (alineado a PLAN-002, DEC-006/007/008 y backlog futuro).
- **Contexto/insumos:** `plan.md` previo con hallazgos P0–P2 y backlog inicial, `agents.md`, `decisions.md`.
- **Acciones realizadas:**
  - Reestructurado `plan.md` como roadmap profesional con visión, principios, fases (F1–F4), grafo de dependencias ampliado, backlog renumerado/ampliado (`PLAN-010+`, `020+`, `030+`, `040+`, `050`), DoD de programa, riesgos y próximo slice.
  - Integrados hallazgos de auditoría (PLAN-002) y dependencias con `DEC-006/007/008` y estrategia de `electron/`.
- **Archivos tocados:**
  - `plan.md` (actualizado)
  - `bitacora.md` (actualizado: esta entrada)
- **Verificación:**
  - Revisión de consistencia documental: fases, dependencias, estados preservados (`PLAN-001/002` done), referencias a decisiones abiertas y alineación con hallazgos P0–P2.
  - Sin cambios de código ni ejecución de pruebas/build (iteración de planificación).
- **Hallazgos / riesgos / deuda:**
  - Persisten P0/P1 técnicos identificados en PLAN-002; requieren implementación prioritaria (PLAN-010/011/012).
  - Decisiones pendientes (`DEC-006/007/008`) condicionan contrato, semántica y alcance de schedules.
- **Decisiones:** ninguna nueva; se mantienen `DEC-006/007/008` en `proposed`.
- **Siguiente paso:** ejecutar **PLAN-010** (corregir P0 en `backend/app/core/scanner.py` y dependencias inmediatas) y preparar borrador de contrato para **PLAN-011**/`DEC-006`/`DEC-007`, registrando evidencia en bitácora.

## 2026-11-11 — Backend/Reviewer (auditoría estática)
- **Objetivo (Plan ID):** PLAN-002 (completado).
- **Contexto/insumos:** revisión estática de `backend/app/core/{scanner,port_scanner,service_detector,os_fingerprint,network_mapper}.py`, `backend/app/tasks.py`, `backend/app/api/{scans,websocket,schedules}.py`, `backend/app/{models,schemas}/scan.py`, `backend/app/celery_app.py`, `backend/app/config.py`; contraste con estado documentado en PLAN-001.
- **Acciones realizadas:**
  - Mapeado el flujo real end-to-end: creación de scan → encolado Celery → ejecución core → persistencia de resultados/progreso → consulta/export API → actualización por WebSocket (polling DB) y estado de schedules (CRUD sin scheduler detectado).
  - Identificadas y priorizadas discrepancias (P0–P2): defectos de ejecución (`COMPREHENSIVE`/`udp_common`, protocolo UDP mal etiquetado), contrato de progreso/callback inconsistente, estrategia de tiempo real y robustez WS, semántica de métricas, ausencia de ejecución programada de schedules, consistencia de cancelación/listados y heurísticas UDP/discovery.
  - Actualizados artefactos de control con hallazgos y próximos pasos.
- **Archivos tocados:**
  - `plan.md` (actualizado: PLAN-002 done, hallazgos 6.x, nuevo slice hacia PLAN-003, historial)
  - `decisions.md` (actualizado: DEC-006/007/008 en estado proposed)
  - `bitacora.md` (actualizado: esta entrada)
- **Verificación:**
  - Auditoría basada en lectura de código y trazado de llamadas/contratos entre módulos (sin ejecución de escaneos de red).
  - No se ejecutaron `pytest`, builds ni pruebas de integración en esta iteración (cambio documental/análisis; entorno de ejecución no ejercitado).
- **Hallazgos / riesgos / deuda:**
  - **P0:** `backend/app/core/scanner.py` usa `udp_common` no definido en modo `COMPREHENSIVE` y asigna protocolo `tcp` a puertos hallados por UDP en ese modo.
  - **P1:** progreso de puertos con callback incompatible/no conectado; WS basado en polling con posibles fallos si el scan no existe; métricas de hosts/progreso con semántica ambigua.
  - **P1:** `Schedule` solo CRUD (sin Celery Beat/scheduler observado) → brecha funcional.
  - **P2:** delete sin transición persistida a `CANCELLED`, respuestas de listado potencialmente pesadas (`results` embebidos), heurísticas de UDP/discovery mejorables.
  - Cualquier validación dinámica posterior debe realizarse solo en redes autorizadas/entornos controlados (DEC-004).
- **Decisiones:** propuestas registradas **DEC-006** (contrato progreso/tiempo real), **DEC-007** (semántica de ejecución y métricas), **DEC-008** (ejecución de schedules). Ninguna aceptada en esta iteración.
- **Siguiente paso:** **PLAN-003** — definir contrato objetivo API/WS/schemas (progreso, métricas, estados, export, schedules), resolver/aceptar decisiones necesarias y planificar correcciones P0/P1 coordinadas backend+frontend, registrando evidencias en próxima iteración.

## 2026-11-11 — Orchestrator/Reviewer (bootstrap)
- **Objetivo (Plan ID):** PLAN-001 (completado), preparación de PLAN-002.
- **Contexto/insumos:** análisis del repositorio `nmap-custom` (estructura, README principal y de `backend/`/`frontend/`, `docs/DOCKER.md`, `docker-compose*.yml`, `Makefile`, `pyproject.toml`, `package.json`, y módulos clave `backend/app/{main,tasks,core/scanner}.py`, `frontend/src/store/scanStore.ts`). Verificación de ausencia previa de archivos de control (`agents.md`, `decisions.md`, `plan.md`, `bitacora.md`).
- **Acciones realizadas:**
  - Analizado el estado actual del proyecto (arquitectura, capacidades, madurez y huecos observables).
  - Definido el flujo operativo basado en **Loop Engineering**, **Harness** y **Graph** (grafo de tareas/dependencias).
  - Creados e inicializados los cuatro archivos de control con estructura, plantillas, seed de backlog, ADRs base y esta entrada de bootstrap.
- **Archivos tocados:**
  - `agents.md` (nuevo)
  - `plan.md` (nuevo)
  - `decisions.md` (nuevo)
  - `bitacora.md` (nuevo)
- **Verificación:**
  - Revisión de consistencia documental: secciones requeridas presentes, referencias cruzadas entre archivos (`agents.md`/`plan.md`/`decisions.md`/`bitacora.md`), backlog inicial `PLAN-001..007`, decisiones `DEC-001..005`, y grafo Mermaid incluido en `plan.md`.
  - No se ejecutaron pruebas de código/build en esta iteración (cambio exclusivamente documental; sin modificaciones en backend/frontend/infra ejecutable).
- **Hallazgos / riesgos / deuda:**
  - `electron/` se encuentra vacío (alcance futuro a decidir, ver PLAN-007 / potencial `DEC`).
  - El roadmap del proyecto indica UI parcialmente incompleta (config/topología/tabla/schedules/export en distintos grados).
  - En `backend/app/core/scanner.py` (modo `COMPREHENSIVE`) se observa referencia a `udp_common` sin definición local visible; requiere auditoría y validación en PLAN-002 antes de asumir comportamiento correcto.
  - Validación funcional de escaneos sujeta a guardrails: solo en redes autorizadas/entornos controlados y con permisos/capacidades adecuados.
- **Decisiones:** DEC-001, DEC-002, DEC-003, DEC-004, DEC-005 registradas (baseline inferido del estado del repositorio y del flujo adoptado).
- **Siguiente paso:** ejecutar **PLAN-002** — auditar `backend/app/core/`, `backend/app/tasks.py`, `api/`, `schemas/` y `models/` para mapear el flujo real (descubrimiento, escaneo, progreso, persistencia, errores), documentar discrepancias y actualizar backlog/decisiones según hallazgos.
