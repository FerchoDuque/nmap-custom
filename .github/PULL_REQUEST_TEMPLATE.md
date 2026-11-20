## Qué cambia

<!-- Una o dos frases. Enlaza el issue/PLAN si existe. -->

## Por qué

<!-- Motivación, trade-offs y alternativas descartadas. -->

## Cómo se verificó

- [ ] `pytest tests/api tests/core` → ___ passed
- [ ] `npm run lint` / `typecheck` / `test:run` / `build`
- [ ] `docker compose config` (si aplica)
- [ ] Prueba manual (si aplica): pasos y resultado

## Checklist

- [ ] La prueba fallaba antes del cambio (TDD) o el cambio es solo documental/config.
- [ ] Sin secretos, credenciales ni IPs de redes reales.
- [ ] `bitacora.md` actualizada; `plan.md` con el estado del `PLAN-xxx`.
- [ ] `decisions.md` con `DEC-xxx` si hay trade-off relevante.
- [ ] `docs/CONTRACT.md` actualizado si cambia el contrato REST/WS.
- [ ] Sin regresiones obvias en el área modificada.
