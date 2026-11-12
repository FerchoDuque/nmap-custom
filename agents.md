# agents.md — Harness y Loop Engineering

> Contrato operativo para agentes humanos/IA que trabajan en este repositorio.
> Leer junto con [`plan.md`](plan.md), [`decisions.md`](decisions.md) y [`bitacora.md`](bitacora.md).

## 1. Contexto del proyecto

- **Proyecto:** Network Scanner (herramienta tipo Nmap para análisis de redes locales).
- **Stack:**
  - **Backend (`backend/`):** Python 3.11+, FastAPI, SQLAlchemy/Alembic, Celery + Redis, motor de escaneo en `app/core/` (`scanner.py`, `port_scanner.py`, `service_detector.py`, `os_fingerprint.py`, `network_mapper.py`).
  - **Frontend (`frontend/`):** React 18 + TypeScript + Vite, Material UI, Zustand, Axios/WebSocket, D3/Recharts.
  - **Infra:** Docker Compose (prod/dev), Nginx, PostgreSQL/SQLite, Makefile (`docs/DOCKER.md`, `DOCKER_QUICKSTART.md`).
- **Directorios clave:** `backend/app/{api,core,models,schemas,tasks.py}`, `frontend/src/{components,services,store,types}`, `docs/`, `electron/` (placeholder).
- **Aviso legal/alcance:** uso exclusivo en redes locales propias o con autorización explícita. No ejecutar escaneos contra objetivos no autorizados.

## 2. Roles de agentes

| Rol | Responsabilidad principal | Áreas típicas |
|---|---|---|
| **Orchestrator** | Descomponer objetivos, priorizar, mantener coherencia entre archivos de control y coordinar handoffs. | `plan.md`, `decisions.md`, `bitacora.md`, coordinación cross-stack |
| **Backend/Scanner** | Lógica de escaneo, API, tareas async, modelos/migraciones, rendimiento y manejo de errores. | `backend/app/**`, `alembic/`, `tests/` |
| **Frontend/UI** | Componentes, estado, integración API/WS, UX y visualización. | `frontend/src/**`, configuración Vite/TS |
| **Infra/QA** | Contenedores, CI-local, build/lint/test, reproducibilidad y observabilidad. | Dockerfiles, `docker-compose*.yml`, `Makefile`, scripts |
| **Reviewer/Security** | Revisión de riesgos: validación de targets, privilegios/capacidades, exposición de servicios, secretos, regresiones. | Cambios transversales, configuración y superficie de ataque |

Un mismo agente puede asumir varios roles en tareas pequeñas, pero debe declarar el rol activo en la bitácora.

## 3. Protocolo del loop (Loop Engineering)

Cada iteración sigue el ciclo **Planificar → Ejecutar → Verificar → Registrar → Consolidar**:

1. **Planificar (entrada)**
   - Seleccionar 1–2 ítems listos en [`plan.md`](plan.md) (sin dependencias bloqueantes).
   - Definir criterio de aceptación y método de verificación antes de cambiar código.
2. **Ejecutar**
   - Aplicar cambios mínimos y coherentes con el estilo/estructura existente.
   - No mezclar refactors amplios con correcciones funcionales sin registrarlo.
3. **Verificar**
   - Ejecutar la matriz de validación aplicable (sección 5).
   - Si no es posible validar (entorno/permisos/dependencias), registrar la limitación y evidencia parcial.
4. **Registrar**
   - Añadir entrada en [`bitacora.md`](bitacora.md) con objetivo, acciones, archivos, verificación y hallazgos.
5. **Consolidar**
   - Actualizar estado/dependencias en [`plan.md`](plan.md).
   - Registrar trade-offs o cambios relevantes en [`decisions.md`](decisions.md) (`DEC-xxx`).
   - No marcar `done` sin verificación registrada.

## 4. Harness (guardrails y políticas)

### Seguridad y alcance
- **Autorización:** no iniciar escaneos reales fuera de redes autorizadas o entornos controlados de prueba.
- **Privilegios:** cambios que afecten `NET_RAW/NET_ADMIN`, raw sockets, descubrimiento o ejecución privilegiada requieren decisión documentada y revisión de riesgo.
- **Entradas:** validar y sanear targets, rangos de puertos y parámetros expuestos por API/UI; evitar inyecciones/comandos inseguros.
- **Secretos/config:** no commitear secretos; usar `.env`/ejemplos existentes; no exponer credenciales en logs.

### Calidad y cambios (TDD obligatorio)
- **TDD (Test-Driven Development) es la práctica por defecto:** para todo cambio funcional o corrección, escribir primero pruebas que fallen (red), implementar el mínimo para pasar (green) y refactorizar con pruebas en verde. Excepción: ajustes puramente documentales/configuración no ejecutable (debe justificarse en bitácora).
- **Cobertura objetivo:** "todo lo crítico y, progresivamente, todo el comportamiento" debe estar respaldado por pruebas automatizadas con **mocks y fixtures** (sin depender de redes reales, servicios externos, privilegios root ni entorno no determinista).
- **Aislamiento:** usar fixtures para datos/config/DB de prueba y mocks/stubs/fakes para sockets, scapy/nmap, Celery/Redis, tiempo, IO y WebSockets según corresponda.
- Respetar convenciones del repo y herramientas existentes (`make`, scripts, linters/tests configurados).
- Preferir cambios localizados y compatibles; documentar supuestos cuando falte contexto.
- Si se detecta trabajo ajeno no relacionado en el árbol, no revertirlo ni sobreescribirlo.

### Criterios de escalamiento al humano
- Requisitos ambiguos o conflicto entre `plan.md` y comportamiento esperado.
- Necesidad de ejecutar acciones con impacto externo/riesgo (escaneo de red real, cambios destructivos, exposición de servicios).
- Decisiones de arquitectura/seguridad con impacto alto o irreversible.

## 5. Matriz de verificación

> Ejecutar lo aplicable al cambio; registrar comandos y resultado en la bitácora.

| Área | Verificaciones sugeridas | Notas |
|---|---|---|
| **Backend** | `pytest` (unit/integration/contract con mocks y fixtures), arranque de API, validación de endpoints/schemas, tareas Celery | Priorizar pruebas deterministas sin red real; Redis/DB reales solo en integración controlada si aplica |
| **Frontend** | `npm run lint`, `npm run build`, `npm run test` (Vitest con mocks/fixtures) | Instalar deps si faltan; mockear API/WS/tiempo para pruebas deterministas |
| **Infra/Docker** | `docker-compose config`, build de servicios, healthchecks, logs básicos | Escaneos SYN/OS pueden requerir capacidades y entorno Linux |
| **Docs/Control** | Consistencia entre `plan/decisions/bitacora`, enlaces y estados | Toda decisión relevante debe tener `DEC-xxx` |

## 6. Definition of Done (DoD)

- [ ] Criterio de aceptación del ítem cumplido.
- [ ] Pruebas automatizadas añadidas/actualizadas (TDD) con **mocks y fixtures** según aplique, y en verde.
- [ ] Verificación ejecutada o limitación documentada con evidencia.
- [ ] Sin regresiones obvias en el área modificada (según alcance).
- [ ] `bitacora.md` actualizada.
- [ ] `plan.md` actualizado (estado/dependencias/notas).
- [ ] `decisions.md` actualizado si hubo trade-off o cambio relevante.
- [ ] Riesgos pendientes y siguientes pasos explícitos.

## 7. Plantilla de handoff entre agentes

```md
### Handoff
- **Fecha/Rol:** 
- **Objetivo (Plan ID):** 
- **Resumen de cambios:** 
- **Archivos tocados:** 
- **Verificación realizada:** (comandos + resultado)
- **Riesgos / deuda / bloqueos:** 
- **Decisiones (DEC):** 
- **Siguiente paso recomendado:** 
```

## 8. Convenciones de los archivos de control

- **`plan.md`:** roadmap y grafo vivo (qué hacer, orden, dependencias, estado).
- **`decisions.md`:** ADRs ligeros (por qué se eligió una opción).
- **`bitacora.md`:** trazabilidad cronológica de iteraciones (qué se hizo y cómo se validó).
- Mantener referencias cruzadas (`PLAN-xxx`, `DEC-xxx`, fechas, rutas de archivo) para continuidad entre sesiones.
