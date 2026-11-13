# Guía visual — Consola cyberpunk cyan

- **Decisión:** DEC-009
- **Implementación:** `frontend/src/theme.ts` (tokens + overrides MUI), `main.tsx` (ThemeProvider)
- **Utilidades de presentación:** `frontend/src/utils/scan.ts`
- **Pruebas:** `frontend/src/utils/*.test.ts`, `frontend/src/services/websocket.test.ts`

## 1. Tokens

| Token | Valor | Uso |
|---|---|---|
| `CYAN` | `#00e5ff` | Acción primaria, acentos, headings, glow |
| `CYAN_DIM` | `#00b8cc` | Variantes/hover de primario |
| `BG_DEFAULT` | `#02040a` | Fondo global (con grid + radial glow) |
| `BG_PAPER` | `#071018` | Superficies: Paper, Card, Dialog, Accordion |
| Texto primario | `#d7fff7` | Lectura principal |
| Texto secundario | `cyan @ 72%` | Metadatos, captions |
| Divider | `cyan @ 18%` | Bordes y separadores |
| Success | `#00ff9c` | `completed`, puerto `open` |
| Warning | `#ffd166` | `cancelled`, puerto `filtered`, avisos legales |
| Error | `#ff4d6d` | `failed`, puerto `closed`, errores |

Tipografía: `Share Tech Mono → JetBrains Mono → Fira Code → Consolas → Courier New` (monoespaciada). Botones en mayúsculas con `letter-spacing`; `h3` en mayúsculas.

## 2. Componentes

- **Paper/Card/Accordion:** borde cyan translúcido + glow sutil; Card intensifica borde/glow en hover. Accordion expandido refuerza el borde.
- **Button:** radios 2px, texto uppercase; `contained` con glow, `outlined` con borde cyan y hover translúcido.
- **Chip:** borde cyan, label uppercase; color semántico según estado.
- **Inputs:** borde cyan translúcido, focus con glow; `InputLabel` uppercase.
- **LinearProgress:** barra fina con glow cyan.
- **Tabla:** cabecera cyan sobre fondo translúcido, filas con divisores tenues.
- **Dialog:** superficie `BG_PAPER`, borde/glow, título cyan uppercase y separadores superior/inferior.
- **Snackbar:** superficie oscura con borde cyan.

## 3. Estados y semántica visual

| Dominio | Valor | Chip |
|---|---|---|
| Scan | `running` | primary |
| Scan | `completed` | success |
| Scan | `failed` | error |
| Scan | `cancelled` | warning |
| Scan | `pending` | default |
| Puerto | `open` | success |
| Puerto | `closed` | error |
| Puerto | `filtered` | warning |
| Puerto | `unknown` | default |

Etiquetas: `formatStatusLabel()` (uppercase, `_` → espacio).

## 4. Patrones de pantalla

- **Cabecera de consola:** título `> SCREEN_NAME` en cyan con glow + caption `[CONTEXTO]` y borde inferior.
- **Secciones:** `> SECTION_NAME` con icono de terminal y contador en Chip.
- **Metadatos:** etiqueta en caption + valor en `h6`/`body2`; prefijo `//` para contexto (`TYPE // tcp_connect`).
- **Estados vacíos:** texto `> NO_*_DETECTED` y acción primaria.
- **Progreso:** barra + porcentaje + host actual (`> 192.168.1.10`).
- **Aviso legal:** Alert warning persistente en Dashboard y en el diálogo de creación.

## 5. Flujo principal (PLAN-021)

1. Dashboard: listado de operaciones activas/recientes, refresco manual y conexión WS por scan activo.
2. `New Scan`: formulario con validación local (`validateScanForm`), aviso de autorización y estados de carga/error.
3. Detalle: resumen de operación, progreso en vivo, cancelación (`PATCH status=cancelled`), hosts/puertos y estados vacíos.
4. Cierre de WS: sin reconexión ante cierre intencional o estado terminal; refresco final para obtener resultados persistidos.
5. Schedules (`/schedules`): listado con configuración/cron/estado/contadores, creación y edición con validación local de cron y target, habilitar/deshabilitar y borrado con confirmación; horas en UTC y aviso de despacho por Beat cada 60 s.
6. Resultados (`/results`): selector de scan, tabla plana host/puerto, búsqueda libre y filtros por estado/protocolo/servicio, contadores de hosts y puertos, y export JSON/CSV/XML con nombre `scan-<id>-<YYYYMMDD>.<formato>`.

## 6. Accesibilidad y contraste

- Texto principal claro sobre fondos muy oscuros; acentos cyan reservados a énfasis y no a bloques de texto largos.
- Contraste alto en tablas y formularios; los chips combinan color + etiqueta textual (no solo color).
- Los campos con error muestran `helperText` explícito y borde de error.
- Evitar glow excesivo en áreas de lectura prolongada; los efectos se limitan a bordes/estados.

## 7. Verificación

```powershell
cd frontend
npm run lint       # ESLint (config en .eslintrc.cjs)
npx tsc --noEmit
npm run build
npx vitest run
```

Cobertura actual de UI/utilidades: clasificación de estados, colores, duración, mapeo WS→Scan, validación de target/puertos (IPv4/IPv6/CIDR/rangos y límite de 1024 hosts), errores de API, validación/formateo de schedules y filtros/export de resultados (54 pruebas).
