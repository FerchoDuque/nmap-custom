# decisions.md — Registro de decisiones (ADR ligero)

> Registro de decisiones técnicas y de producto. Complementa [`plan.md`](plan.md) y se referencia desde [`bitacora.md`](bitacora.md).

## Convenciones

- **ID:** `DEC-XXX` (incremental, no reutilizar).
- **Estados:** `proposed` | `accepted` | `superseded` | `deprecated`.
- Toda decisión que afecte arquitectura, seguridad, dependencias mayores, modelo de datos o UX principal debe registrarse aquí.
- Si una decisión cambia el grafo de trabajo, actualizar el **Impacto en plan/grafo** y [`plan.md`](plan.md).

## Índice

| ID | Fecha | Estado | Título |
|---|---|---|---|
| DEC-001 | 2026-11-11 | accepted | Arquitectura backend asíncrona para escaneos |
| DEC-002 | 2026-11-11 | accepted | Stack frontend para operación y visualización |
| DEC-003 | 2026-11-11 | accepted | Despliegue contenerizado con capacidades de red controladas |
| DEC-004 | 2026-11-11 | accepted | Alcance operativo limitado a redes autorizadas |
| DEC-005 | 2026-11-11 | accepted | Adopción de harness, loop engineering y grafo documental |
| DEC-006 | 2026-11-11 | accepted | Contrato de progreso y tiempo real (API/WS/tareas, baseline) |
| DEC-007 | 2026-11-11 | accepted | Semántica de ejecución de escaneo y métricas (baseline) |
| DEC-008 | 2026-11-11 | accepted | Estrategia de ejecución para scans programados (Celery Beat + despachador DB) |
| DEC-009 | 2026-11-11 | accepted | Dirección visual UI: consola cyberpunk cyan |
| DEC-010 | 2026-11-11 | accepted | Estrategia TDD con mocks y fixtures para cobertura integral |

---

## DEC-001 — Arquitectura backend asíncrona para escaneos
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** el escaneo de red es una operación potencialmente larga, con múltiples hosts/puertos y necesidad de reportar progreso y persistir resultados.
- **Decisión:** usar **FastAPI** como capa API/WS, **Celery + Redis** para ejecución asíncrona de tareas, y **SQLAlchemy/Alembic** para persistencia/modelado (SQLite en dev local, PostgreSQL en despliegue Docker). El motor de escaneo se organiza en módulos de `backend/app/core/`.
- **Alternativas consideradas:**
  - Ejecución síncrona en el request HTTP (descartada por tiempos de espera/bloqueo).
  - Otro framework/stack de workers (no adoptado; se prioriza lo ya presente en el repo).
- **Consecuencias:**
  - (+) Mejor manejo de trabajos largos, progreso y separación de responsabilidades.
  - (+) Base para escalar workers y aislar carga.
  - (-) Mayor complejidad operativa (broker, worker, estados de tarea, consistencia).
- **Impacto en plan/grafo:** nodos `CORE -> TASK -> API` y `DB -> API/CORE`; condiciona PLAN-002/003/006.
- **Verificación:** endpoints de creación/consulta de scans operativos, tareas procesadas por worker, estados/progreso persistidos y expuestos.

## DEC-002 — Stack frontend para operación y visualización
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** se requiere una interfaz web para configurar escaneos, monitorear progreso en tiempo real y explorar resultados/topología.
- **Decisión:** usar **React 18 + TypeScript + Vite**, **Material UI** para componentes, **Zustand** para estado, servicios dedicados para **REST/WebSocket**, y librerías de visualización (**D3/Recharts**) según necesidad.
- **Alternativas consideradas:**
  - UI mínima sin framework SPA (descartada por complejidad de estado/tiempo real).
  - Otros manejadores de estado/bundlers (no priorizados frente a la base existente).
- **Consecuencias:**
  - (+) Tipado y estructura modular para crecer en vistas/funcionalidad.
  - (+) Integración natural con actualizaciones en tiempo real.
  - (-) Requiere mantener alineación estricta de contratos con backend.
- **Impacto en plan/grafo:** nodos `API -> STORE -> UI -> VIZ`; condiciona PLAN-003/004/005.
- **Verificación:** build/lint/tests frontend y flujo funcional de escaneo/visualización contra API real o mock acordado.

## DEC-003 — Despliegue contenerizado con capacidades de red controladas
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** el proyecto incluye componentes con dependencias de runtime (DB, Redis, Nginx) y técnicas de escaneo que pueden requerir privilegios de red.
- **Decisión:** proveer ejecución mediante **Docker Compose** (prod/dev) con separación de servicios y, cuando sea necesario para tipos de escaneo avanzados, otorgar capacidades `NET_RAW/NET_ADMIN` de forma explícita y controlada.
- **Alternativas consideradas:**
  - Ejecución solo local sin contenedores (menos reproducible para integración completa).
  - Contenedores siempre privilegiados (descartado por principio de mínimo privilegio).
- **Consecuencias:**
  - (+) Reproducibilidad y despliegue integrado de dependencias.
  - (-) Complejidad adicional de red/permisos y diferencias entre entornos.
  - (-) Riesgo de seguridad si se amplían capacidades sin controles.
- **Impacto en plan/grafo:** nodo `DOC/Infra -> TEST` y dependencias de validación; relevante para PLAN-002/006.
- **Verificación:** `docker-compose config`, builds/healthchecks y documentación de requisitos de capacidades por tipo de escaneo.

## DEC-004 — Alcance operativo limitado a redes autorizadas
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** la funcionalidad del proyecto puede usarse indebidamente si se ejecuta contra redes sin permiso.
- **Decisión:** restringir el uso previsto y las prácticas de prueba/validación a **redes locales propias o explícitamente autorizadas**; mantener avisos legales y evitar ejemplos o automatizaciones que promuevan uso no autorizado.
- **Alternativas consideradas:**
  - Omitir controles/documentación de alcance (descartado por riesgo legal/ético).
- **Consecuencias:**
  - (+) Reduce riesgo de uso indebido y alinea el proyecto con fines legítimos.
  - (-) Limita escenarios de prueba a entornos controlados.
- **Impacto en plan/grafo:** guardrail transversal en `agents.md`; aplica a PLAN-002/003/004/006.
- **Verificación:** presencia de disclaimers/documentación, y registro en bitácora de que las validaciones se realizan en entornos autorizados.

## DEC-005 — Adopción de harness, loop engineering y grafo documental
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** se requiere un flujo consistente para trabajo multi-agente con trazabilidad, dependencias claras y decisiones explícitas.
- **Decisión:** adoptar cuatro artefactos de control: `agents.md` (harness/roles/protocolo), `plan.md` (backlog + grafo), `decisions.md` (ADRs) y `bitacora.md` (log de iteraciones), con referencias cruzadas (`PLAN-xxx`, `DEC-xxx`).
- **Alternativas consideradas:**
  - Documentación ad-hoc sin estructura ni trazabilidad (descartada por pérdida de contexto).
  - Tooling externo inmediato para grafos/gestión (pospuesto; iniciar con Markdown versionado).
- **Consecuencias:**
  - (+) Continuidad entre sesiones/agentes y mejor control de dependencias.
  - (+) Decisiones y verificaciones auditables.
  - (-) Requiere disciplina de actualización en cada iteración.
- **Impacto en plan/grafo:** habilita y gobierna todos los nodos del plan; PLAN-001 completado.
- **Verificación:** archivos creados, enlazados y usados en el ciclo de trabajo (evidencia en bitácora y actualizaciones de plan/decisiones).

---

## DEC-006 — Contrato de progreso y tiempo real (API/WS/tareas, baseline)
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** la auditoría (PLAN-002) detectó polling de DB en WS, broadcast no integrado, robustez limitada y payloads inconsistentes.
- **Decisión (baseline):**
  - **Estrategia de tiempo real:** mantener **polling de DB** como mecanismo baseline en `WS /ws/scan/{id}` (fuente de verdad: persistencia), con validación de existencia del scan y cierre controlado si no existe.
  - **Mensajes WS:** `{"type":"status"|"update", scan_id, status, progress, current_host, hosts_scanned, hosts_total, ports_found, error_message}`; en ausencia se envía `{"type":"error", scan_id, message}`. Clientes deben tolerar campos opcionales y estados terminales `completed|failed|cancelled`.
  - **Ciclo de vida/cancelación (API):** `PATCH /api/scans/{id}` con `status=cancelled` (si `pending/running`) revoca tarea si aplica, persiste `cancelled`, `completed_at` y `error_message` coherente; `DELETE` revoca si activo y elimina el recurso.
  - **Evolución:** integración de broadcast/pub-sub, progreso fino por puertos y refinamiento de métricas quedan como mejoras incrementales sujetas a pruebas de contrato.
- **Alternativas consideradas:** pub/sub inmediato; mantener contrato implícito sin validaciones (descartado).
- **Consecuencias:**
  - (+) Contrato más explícito y robusto, alineado con implementación actual y UI.
  - (-) Polling no es óptimo a escala; aún hay deuda de progreso fino y tipado compartido formal.
- **Impacto en plan/grafo:** habilita PLAN-012/020 y guía PLAN-011 (tests de contrato y refinamientos).
- **Verificación:** pruebas API/lifecycle backend (5) + core (28) en verde con mocks/fixtures; revisión de payload WS en código; validación E2E en entorno autorizado pendiente.

## DEC-007 — Semántica de ejecución de escaneo y métricas (baseline)
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** la auditoría (PLAN-002) identificó defectos y ambigüedades en ejecución, protocolos, heurísticas UDP y métricas.
- **Decisión (baseline implementada y testeada en core):**
  - **Tipos de scan:** `TCP_CONNECT` → escaneo TCP connect con puertos solicitados; `TCP_SYN` → SYN (fallback según implementación) con puertos solicitados; `UDP` → escaneo UDP con puertos solicitados; `COMPREHENSIVE` → TCP SYN sobre puertos solicitados + UDP sobre baseline `DEFAULT_UDP_PORTS`.
  - **Protocolo:** cada hallazgo preserva su protocolo de origen (`tcp`/`udp`), incluyendo resultados mixtos en `COMPREHENSIVE`.
  - **Estados:** se mantienen estados `open/closed/filtered/unknown` según motor; **heurística UDP actual**: respuesta → `open`, timeout → `open` (ambigüedad open|filtered documentada), error de socket → `closed`, excepción → `unknown` (sujeto a refinamiento futuro por decisión explícita si cambia).
  - **Métricas (baseline actual):** `hosts_total` = hosts parseados del target; `hosts_up` = hosts descubiertos activos; `total_ports_found` = cantidad de puertos reportados como abiertos en resultados; `hosts_scanned/progress` según orquestación/tarea vigente. Refinamientos de contrato fino se gestionan en PLAN-011/012.
  - **Validaciones futuras:** rangos/inputs, opciones no aplicadas (p.ej. `aggressive`) y optimizaciones de descubrimiento se tratan en iteraciones posteriores con tests.
- **Alternativas consideradas:** redefinir inmediatamente heurística UDP a `open|filtered` o introducir sondeos adicionales (pospuesto para no ampliar riesgo sin evidencia/control).
- **Consecuencias:**
  - (+) Corrige P0 y establece comportamiento determinista y probado para protocolos/comprehensive.
  - (+) Permite cerrar PLAN-010 con base verificable.
  - (-) Persisten deudas conocidas (heurística UDP, semántica fina de progreso, opciones no aplicadas) a abordar en PLAN-011/012/031.
- **Impacto en plan/grafo:** desbloquea avance de `PLAN-011/012/020/030`; mantiene trazabilidad de deudas.
- **Verificación:** `backend/tests/core` (28 pruebas) en verde con mocks/fixtures, incluyendo casos de `COMPREHENSIVE`/protocolos/UDP; `py_compile` OK. Validación en red real solo en entornos autorizados.

## DEC-008 — Estrategia de ejecución para scans programados
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** existen modelo y API CRUD para `Schedule` (`cron_expression`, `scan_config`), pero no hay componente que ejecute los disparos programados.
- **Decisión:** **Opción A — Celery Beat + despachador periódico basado en DB.** La base de datos es la fuente de verdad:
  - Una tarea Beat (`dispatch_due_schedules`) se ejecuta cada minuto.
  - Selecciona schedules `enabled` con `next_run_at <= now`, crea el scan usando el mismo camino que la API (`perform_scan_task.delay`), y actualiza `last_run_at`, `next_run_at`, `total_runs`/`successful_runs`/`failed_runs`.
  - Debe ser **idempotente**: actualización condicional/claim por schedule (`UPDATE ... WHERE next_run_at = valor_leído`) o lock para evitar dobles disparos con más de un worker Beat.
  - Cálculo de `next_run_at` con `croniter` (nueva dependencia backend) y zona horaria UTC.
- **Fases de implementación (PLAN-023):**
  1. ✅ **Servicio de despacho + cálculo de próxima ejecución + tests con reloj y Celery mockeados** (`app/core/scheduler.py`, `tests/core/test_scheduler.py`, `tests/core/test_dispatch_task.py`).
  2. ✅ **Wiring de Beat en `docker-compose`** (servicio `beat` en prod/dev, sin `cap_add`) y `beat_schedule` cada 60 s.
  3. ✅ **UI de schedules** (`/schedules`: listado, alta/edición, habilitar/deshabilitar, borrado, cron presets y próxima ejecución en UTC) en PLAN-023/022.
- **Guardrail (cumplido en fase 3):** mientras el despachador no estuviera desplegado, la API/UI no debía prometer ejecución automática. La vista `/schedules` ya refleja ejecución por Beat, estado y próxima ejecución.
- **Alternativas consideradas:** (B) declarar schedules como configuración sin ejecución automática — descartada por dejar una brecha funcional visible; ejecución manual ad-hoc desde API — descartada como solución final (solo útil como mitigación temporal).
- **Consecuencias:**
  - (+) Alinea funcionalidad prometida con comportamiento real y mantiene la DB como fuente de verdad.
  - (-) Añade complejidad operativa (Beat, cálculo cron, idempotencia, tests de tiempo) y una dependencia (`croniter`).
- **Impacto en plan/grafo:** desbloquea `PLAN-023`; afecta `API/DB`, `Infra` (PLAN-040/041) y `UI` (PLAN-022).
- **Verificación:** tests unitarios del cálculo de `next_run_at` e idempotencia con mocks; prueba del despacho creando scans mockeados; prueba de disparo controlado en entorno autorizado (DEC-004) antes de release.

---

## DEC-009 — Dirección visual UI: consola cyberpunk cyan
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** se requiere una identidad visual distintiva y consistente para la interfaz web al profesionalizar el producto.
- **Decisión:** adoptar un look & feel **"consola cyberpunk cyan"**: paleta dominante cyan/neón sobre fondos oscuros, estética de terminal/futurista, tipografía monoespaciada/tech donde aporte legibilidad, alto contraste, acentos luminosos controlados y consistencia en componentes (dashboard, formularios, progreso, tablas, detalle, visualizaciones).
- **Alternativas consideradas:** mantener tema Material UI dark genérico; otros temas (no solicitados).
- **Consecuencias:**
  - (+) Identidad clara y diferenciada, alineada a dominio de red/security tooling.
  - (-) Requiere definir tokens de diseño (colores, tipografía, spacing, estados) y aplicarlos de forma coherente para evitar inconsistencias o problemas de accesibilidad/contraste.
- **Impacto en plan/grafo:** guía transversal para `FE -> UI -> VIZ` (PLAN-020/021/022) y documentación de UI.
- **Verificación:** guía de estilos/tokens aplicada en componentes clave, revisión visual y de contraste/accesibilidad básica.

---

## DEC-010 — Estrategia TDD con mocks y fixtures para cobertura integral
- **Fecha:** 2026-11-11
- **Estado:** accepted
- **Contexto:** se requiere asegurar que todo el comportamiento del sistema funcione de forma confiable y verificable durante la profesionalización, sin depender de redes reales, servicios externos o entornos no deterministas.
- **Decisión:** adoptar **TDD (red-green-refactor)** como práctica obligatoria para cambios funcionales y construir una suite de pruebas que cubra progresivamente todo el comportamiento soportado usando **mocks y fixtures**. Las pruebas deben ser deterministas y aislar dependencias (sockets/scapy/nmap, Celery/Redis, DB según nivel, tiempo, IO, WebSocket/API externas). La pirámide incluirá unit, integration y contract/smoke/e2e según corresponda.
- **Alternativas consideradas:** pruebas manuales/ad-hoc; pruebas solo de integración con dependencias reales (descartadas como base por costo, flakiness y requisitos de privilegios/red).
- **Consecuencias:**
  - (+) Mayor confianza, regresiones detectadas temprano, diseño más testeable, habilita CI reproducible.
  - (-) Inversión inicial en harness/fixtures y mantenimiento de tests; requiere disciplina en cada iteración.
- **Impacto en plan/grafo:** transversal a todo el grafo; impulsa `PLAN-030` y condiciona `PLAN-010..050` (ningún ítem funcional se considera cerrado sin pruebas adecuadas).
- **Verificación:** presencia y ejecución en verde de suites automatizadas (`pytest`, `vitest`, etc.) con uso de mocks/fixtures; evidencias en `bitacora.md` y checks de CI.

---

## DEC-011 — Límites de recursos explícitos y configuración segura por entorno
- **Fecha:** 2026-11-13
- **Estado:** accepted
- **Contexto:** el motor limitaba rangos grandes truncando silenciosamente a 1024 hosts y la API aceptaba cualquier valor de CORS/`SECRET_KEY`, lo que podía encolar trabajo desproporcionado o exponer el servicio.
- **Decisión:**
  - Rechazar con `422` (nunca truncar) targets por encima de `MAX_HOSTS_PER_SCAN` (default `1024`) y listas por encima de `MAX_PORTS_PER_SCAN` (default `65535`), configurables por entorno y aplicadas de forma uniforme a scans y schedules.
  - Exigir orígenes CORS explícitos; `*` y listas vacías fallan al cargar la configuración.
  - Detectar el `SECRET_KEY` placeholder y emitir warning al arrancar en `ENV=production`.
  - Mantener mínimo privilegio en contenedores: `NET_RAW`/`NET_ADMIN` solo en backend/celery; `beat` sin capacidades.
- **Alternativas consideradas:** truncar como hacía el mapper (descartado: resultados incompletos y silenciosos); permitir `*` con credenciales (descartado: exposición amplia); límites solo en UI (descartado: no protege API/directos).
- **Consecuencias:**
  - (+) Comportamiento predecible, protección de recursos y configuración segura por defecto; errores accionables para el operador.
  - (-) Rangos legítimamente grandes requieren subdividir el escaneo o elevar el límite de forma consciente; puede romper expectativas previas de truncado.
- **Impacto en plan/grafo:** cierra `PLAN-031`; condiciona `PLAN-032` (mensajes/timeouts) y `PLAN-050` (config de release).
- **Verificación:** `backend/tests/core/test_config.py`, `test_validation.py` y `test_input_validation.py`; `frontend/src/utils/validation.test.ts`; suite backend **162 passed** y frontend **54 passed**.

---

## DEC-012 — Observabilidad con logging JSON, health con dependencia real y métricas agregadas
- **Fecha:** 2026-11-13
- **Estado:** accepted
- **Contexto:** los logs eran texto libre sin correlación, `/api/health` devolvía `healthy` sin comprobar la base y no había una vista agregada para smoke checks; añadir dependencias de observabilidad (structlog, prometheus_client, OpenTelemetry) en este punto incrementaba superficie y mantenimiento.
- **Decisión:**
  - Emitir **una línea JSON** por registro usando solo la librería estándar (`JsonFormatter`), con campos base (`timestamp`, `level`, `logger`, `message`) y correlación opcional (`scan_id`, `task_id`, `event`, `status`, `duration_ms`, `hosts_found`, `ports_found`, `exception`).
  - Correlacionar tareas con `get_scan_logger(scan_id, task_id=...)` y eventos `scan.*`; el logger es inyectable para tests/sinks.
  - `/api/health` ejecuta `SELECT 1` y responde `503` cuando la base no está disponible; el contenedor usa esa señal vía `HEALTHCHECK` sin dependencias extra.
  - `/api/metrics` expone agregados de solo lectura (`total`, `by_status`, `active`, `hosts_up_total`, `ports_found_total`), sin `results`.
- **Alternativas consideradas:** structlog/prometheus_client (descartado por dependencia y alcance); health estático (descartado: no detecta fallos de DB); logging texto + grep manual (descartado: difícil de filtrar por scan).
- **Consecuencias:**
  - (+) Señales filtrables por `scan_id`, health accionable y métricas sin dependencias nuevas; compatible con Python 3.11–3.14.
  - (-) Sin histogramas/exportador Prometheus ni nivel de log configurable aún; `by_status` puede crecer si se añaden estados.
- **Actualización (2026-11-14):** el nivel de log ya es configurable con `LOG_LEVEL` (`DEBUG`…`CRITICAL`, default `INFO`; inválido impide arrancar). Queda pendiente solo el exportador Prometheus/OpenTelemetry. Verificación: `test_config.py::TestLogLevel` (6).
- **Impacto en plan/grafo:** cierra `PLAN-040`; alimenta `PLAN-042` (runbooks) y `PLAN-050` (release).
- **Verificación:** `backend/tests/core/test_logging_utils.py` (9) y `backend/tests/api/test_system.py` (4); suite backend **175 passed** con SQLite in-memory y DB simulada.

---

## DEC-013 — Resiliencia: timeout acotado, idempotencia terminal y errores no sensibles
- **Fecha:** 2026-11-13
- **Estado:** accepted
- **Contexto:** una entrega duplicada de Celery podía reejecutar un scan terminado, un scan colgado no tenía límite de tiempo, un fallo por host abortaba todo el escaneo y los errores internos podían filtrarse al cliente o a la base. Además, el DNS inverso sin control hacía depender los tests de red real.
- **Decisión:**
  - Ejecutar cada scan con `asyncio.wait_for` sobre `DEFAULT_SCAN_TIMEOUT` (default `300` s); al excederse, marcarlo `failed` con mensaje acotado y lanzar `ScanTimeoutError`.
  - No reejecutar scans en estado terminal (`completed`/`failed`/`cancelled`): devolver `{"status": "skipped"}` y emitir `scan.skipped`.
  - Aislar fallos por host (se omiten y cuentan en `hosts_failed`) para que el resto del scan continúe.
  - Responder `500 {"detail": "Internal server error"}` en errores no controlados, dejando el traceback solo en logs; truncar mensajes persistidos a 500 caracteres y enmascarar errores de SQLAlchemy.
  - Hacer configurable el DNS inverso con `RESOLVE_HOSTNAMES` (default `true`) y desactivarlo en las pruebas.
- **Alternativas consideradas:** reintentos automáticos de la tarea (descartado: reejecuta trabajo y duplica resultados sin presupuesto claro); cancelación cooperativa del motor por socket (fuera de alcance); devolver `str(exc)` siempre (descartado: filtra internos).
- **Consecuencias:**
  - (+) Workers no quedan colgados, no hay resultados duplicados, el cliente recibe errores seguros y los tests son deterministas/rápidos.
  - (-) Un scan que excede el presupuesto se pierde (queda `failed`) y no se reanuda; hosts omitidos requieren reescaneo manual; el timeout no interrumpe un socket bloqueado de inmediato.
- **Impacto en plan/grafo:** cierra `PLAN-032`; habilita `PLAN-042` (runbooks de fallos) y `PLAN-050` (release).
- **Verificación:** `tests/core/test_resilience.py` (9) y `tests/api/test_error_handling.py` (3); backend **190 passed** en ~2.4 s sin red real.

---

## DEC-014 — `electron/` aplazado fuera del alcance 0.1.0 (sin entregable ni placeholder activo)
- **Fecha:** 2026-11-13
- **Estado:** accepted
- **Contexto:** `electron/` existía como directorio vacío y no versionado (git no registra directorios vacíos); el README lo anunciaba como "future" y el roadmap lo listaba como pendiente. Mantener esa ambigüedad sugiere un entregable inexistente y compite con el objetivo real de 0.1.0: backend/frontend web estables, observables y desplegables.
- **Decisión:** aplazar el empaquetado Electron fuera del alcance activo de 0.1.0.
  - No se mantiene un placeholder vacío ni se crea estructura de empaquetado.
  - README y roadmap lo marcan explícitamente como **aplazado** y remiten a esta decisión.
  - Se reevaluará solo con una `DEC` nueva que defina alcance, distribución (firma/auto-update) y coste de mantenimiento.
- **Alternativas consideradas:** implementar ahora (descartado: multiplica superficie de build/distribución sin validar antes el flujo web); retirarlo del todo del roadmap (descartado: pierde la intención de producto a futuro).
- **Consecuencias:**
  - (+) Alcance de release nítido: nada en el árbol sugiere un entregable Electron; no hay deuda de empaquetado sin dueño.
  - (-) Si se retoma, hay que crear el proyecto desde cero (sin andamiaje previo).
- **Impacto en plan/grafo:** cierra `PLAN-043`; no bloquea ningún otro ítem (dependencia `PLAN-001`).
- **Verificación:** `Test-Path electron` → `True` (directorio vacío) y `git ls-files electron` → vacío; README usa ahora "aplazado (DEC-014)".

---

## Plantilla para nuevas decisiones

```md
## DEC-XXX — Título
- **Fecha:** YYYY-MM-DD
- **Estado:** proposed | accepted | superseded | deprecated
- **Contexto:** 
- **Decisión:** 
- **Alternativas consideradas:** 
- **Consecuencias:** 
- **Impacto en plan/grafo:** 
- **Verificación:** 
```
