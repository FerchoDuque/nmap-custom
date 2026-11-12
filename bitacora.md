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
