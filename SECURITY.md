# Política de seguridad

## Versiones soportadas

| Versión | Soporte |
|---|---|
| `0.1.x` | Sí (parches de seguridad) |
| `< 0.1` | No |

## Cómo reportar una vulnerabilidad

**No abras un issue público.** Usa
[GitHub Security Advisories](https://github.com/FerchoDuque/nmap-custom/security/advisories/new)
(private vulnerability reporting) e incluye:

- Versión/commit afectado y despliegue (compose, bare metal).
- Pasos de reproducción mínimos y prueba de concepto.
- Impacto esperado (confidencialidad, integridad, disponibilidad).
- Configuración relevante **sin secretos** (`SECRET_KEY`, credenciales de DB).

Acuse de recibo en **72 h** y evaluación inicial en **7 días**. Si el reporte es
aceptado, coordinamos divulgación y crédito en la release que lo corrige.

## Alcance

Este proyecto es un **escáner de red**. Solo debe usarse en redes propias o con
autorización explícita (ver `decisions.md`, DEC-004).

**En alcance:**

- API, WebSocket y UI del proyecto (inyección, SSRF hacia la API, bypass de
  validación de targets/puertos, XSS, CSRF, fugas de información en errores).
- Contenedores e imágenes publicadas (privilegios, `NET_RAW`/`NET_ADMIN`,
  secretos embebidos, dependencias vulnerables).
- Controles de alcance: ausencia de límites, escaneos fuera de rango permitido.

**Fuera de alcance:**

- Vulnerabilidades en `nmap`, `python-nmap` o en los sistemas escaneados.
- Hallazgos obtenidos escaneando redes de terceros sin autorización.
- Ataques de denegación de servicio o ingeniería social.
- Reportes generados solo por escáneres automáticos sin impacto demostrado.

## Buenas prácticas de despliegue

- Cambia `SECRET_KEY` (el backend avisa si sigue siendo el placeholder).
- Restringe `CORS_ORIGINS` a tus dominios; no uses `*`.
- No expongas el backend a Internet sin TLS y autenticación (ver roadmap 0.2.0).
- Mantén `NET_RAW`/`NET_ADMIN` solo en `backend`/`celery`; nunca en `beat`.

## Historial

Las correcciones de seguridad se documentan en `CHANGELOG.md` (sección
`Security`) y en las notas de cada release.
