# CI y verificación local (PLAN-041)

Pipeline reproducible para validar el repositorio **sin Docker, sin red y sin privilegios**.
El mismo conjunto de checks se ejecuta en local y en GitHub Actions.

## Comandos

| Entorno | Comando |
|---|---|
| Windows (PowerShell) | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1` |
| Linux/macOS/WSL | `bash scripts/verify.sh` |
| Sin build (más rápido) | añadir `-SkipBuild` o `--skip-build` |
| Make (sin build) | `make check` |
| Make (con build) | `make verify` |

## Qué ejecuta

| Paso | Comando | Ámbito |
|---|---|---|
| Backend tests | `python -m pytest tests/api tests/core -q` | API, contrato, WS, validación, scheduler |
| Frontend lint | `npm run lint` | ESLint sin warnings |
| Frontend typecheck | `npm run typecheck` | `tsc --noEmit` |
| Frontend tests | `npm run test:run` | Vitest en modo one-shot (utilidades + componentes con jsdom) |
| Frontend build | `npm run build` | `tsc` + bundle Vite |

Los tests de backend fijan por defecto `DATABASE_URL=sqlite:///:memory:` en
`backend/tests/conftest.py`; los scripts también exportan `PYTHONPATH=.` y la
misma URL para que el resultado no dependa del entorno del operador.

## CI

`.github/workflows/ci.yml` se dispara en `push` a `main` y en `pull_request`:

- **backend:** Python 3.11, `pip install -r backend/requirements.txt`, pytest con
  `PYTHONPATH=.` y SQLite en memoria.
- **frontend:** Node 20, `npm ci`, lint, typecheck, tests y build.

No se ejecutan escaneos de red, resolución DNS ni contenedores con capacidades.

## Alcance y limitaciones

- No hay E2E real de red/WebSocket ni disparo real de Beat: requiere un entorno
  autorizado (DEC-004) y se valida aparte.
- El job de CI no construye imágenes Docker; para eso usar `make build`/`make build-dev`.
- El build de frontend puede mostrar el aviso de chunk > 500 kB; es deuda conocida
  (code-splitting pendiente), no un fallo.
- La primera ejecución local requiere dependencias instaladas (`pip install -r
  backend/requirements.txt`, `npm ci`).

## Solución de problemas

- **`ModuleNotFoundError: app`** → ejecutar desde `backend/` con `PYTHONPATH=.`
  (los scripts ya lo hacen).
- **Vitest no termina** → usar `npm run test:run`, no `npm test` (watch mode).
- **`tsc` falla en tests** → los literales de enums deben usar los valores de
  `src/types` (p. ej. `PortState.OPEN`).
