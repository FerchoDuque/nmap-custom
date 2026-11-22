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

`.github/workflows/ci.yml` se dispara en `push` a `main`, en `pull_request` y
puede reutilizarse (`workflow_call`) desde el release:

- **backend:** Python 3.11, `uv export --frozen --extra dev` desde `uv.lock`
  (lockfile único, pins exactos) y pytest con `PYTHONPATH=.` y SQLite en memoria.
- **frontend:** Node 20, `npm ci`, lint, typecheck, tests y build.
- **compose config:** valida `docker-compose.yml` y `docker-compose.dev.yml`.

Workflows complementarios:

| Workflow | Disparador | Qué hace |
|---|---|---|
| `codeql.yml` | push a `main`, PR y lunes 04:23 UTC | CodeQL `security-extended` para Python y JS/TS |
| `docker.yml` | push a `main`/tags y PR que toque backend/frontend | Buildx, SBOM y provenance; push a GHCR en `main`/tags |
| `release.yml` | tags `v*` | Reejecuta CI, valida tag = versión, publica notas del CHANGELOG y crea GitHub Release |

`dependabot.yml` abre PRs semanales agrupadas para pip, npm, GitHub Actions y
mensuales para las imágenes base.

`main` está protegido: PR obligatorio y checks **Backend tests**, **Frontend
checks** y **Compose config** en verde (el propietario conserva bypass de admin;
ver DEC-016). No se permite force-push ni borrar la rama.

No se ejecutan escaneos de red, resolución DNS ni contenedores con capacidades.

## Alcance y limitaciones

- No hay E2E real de red/WebSocket ni disparo real de Beat: requiere un entorno
  autorizado (DEC-004) y se valida aparte. El objetivo de 0.2.0 es un perfil
  `lab` dentro de la red Docker, sin red externa.
- `docker.yml` construye y publica imágenes, pero no ejecuta la suite dentro de
  ellas ni firma con cosign todavía.
- Cobertura de backend aún no se mide en CI (`pytest-cov` está en dev; falta
  fijar umbral).
- **El bundle usa code-splitting** (rutas lazy y chunks de vendor); el mayor chunk actual es ~241 kB. Si reaparece el aviso >500 kB, revisar imports estáticos pesados.
- La primera ejecución local requiere dependencias instaladas (`uv sync --extra
  dev` en `backend/`, `npm ci` en `frontend/`).

## Solución de problemas

- **`ModuleNotFoundError: app`** → ejecutar desde `backend/` con `PYTHONPATH=.`
  (los scripts ya lo hacen).
- **Vitest no termina** → usar `npm run test:run`, no `npm test` (watch mode).
- **`tsc` falla en tests** → los literales de enums deben usar los valores de
  `src/types` (p. ej. `PortState.OPEN`).
