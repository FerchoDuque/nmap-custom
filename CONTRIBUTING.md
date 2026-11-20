# Contribuir

Gracias por el interés. Este repositorio sigue el contrato de `agents.md`:
iteraciones con **Planificar → Ejecutar → Verificar → Registrar → Consolidar** y
**TDD obligatorio** para cambios funcionales.

## Requisitos

- Python 3.11+ y Node 20+.
- Docker (solo si vas a validar el stack).
- Opcional: `uv` para regenerar el lockfile.

## Puesta en marcha

```bash
# Backend
cd backend
python -m venv .venv
. .venv/Scripts/activate        # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements-dev.txt
PYTHONPATH=. DATABASE_URL=sqlite:///:memory: pytest tests/api tests/core -q

# Frontend
cd frontend
npm ci
npm run lint && npm run typecheck && npm run test:run && npm run build
```

Verificación completa (Windows): `powershell -NoProfile -File scripts/verify.ps1`.

## Flujo de trabajo

1. Abre un issue o elige un `PLAN-xxx` en `plan.md`.
2. Crea una rama: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
3. **Escribe primero la prueba** que falla; luego el mínimo cambio que la pasa.
4. Usa mocks/fixtures: sin red real, sin servicios externos, sin privilegios root.
5. Ejecuta la matriz de verificación aplicable y actualiza `bitacora.md` y `plan.md`.
6. Abre un PR (obligatorio en `main`) con el resumen y la evidencia.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/):
`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`, `perf:`, `ci:`.
Un commit = un cambio con sentido propio; el cuerpo explica el **porqué**.

## Checklist de PR

- [ ] Pruebas nuevas/actualizadas que fallaban antes del cambio (TDD).
- [ ] `pytest`, `lint`, `typecheck`, `test:run` y `build` en verde.
- [ ] Sin secretos, credenciales ni datos de redes reales.
- [ ] `bitacora.md` / `plan.md` actualizados; `decisions.md` si hay trade-off.
- [ ] Documentación afectada actualizada (`docs/`).
- [ ] Cambios de contrato REST/WS reflejados en `docs/CONTRACT.md`.

## Alcance y ética

No se aceptan contribuciones que faciliten escaneos no autorizados, evasión de
controles, exfiltración de datos o explotación de sistemas. El proyecto está
pensado para redes propias o auditorías con autorización escrita.

## Licencia

Al contribuir aceptas que tu aportación se distribuye bajo **GPL-3.0** (ver
`LICENSE`).
