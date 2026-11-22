# Datos: migraciones, backup/restore y retención

Ciclo de vida de la base de datos (PLAN-062). Todo lo descrito aquí puede
validarse **sin red, sin PostgreSQL y sin privilegios**: las pruebas usan
SQLite temporal y mocks de `pg_dump`/`pg_restore`.

## 1. Esquema con Alembic

| Elemento | Ruta |
|---|---|
| Configuración | `backend/alembic.ini` |
| Entorno | `backend/migrations/env.py` |
| Revisiones | `backend/migrations/versions/` |
| Baseline | `backend/migrations/versions/0001_baseline.py` |
| Lógica de adopción | `backend/app/core/db_migrations.py` |

La URL de la base se toma de `DATABASE_URL` / `app.config.settings`, así que
las migraciones apuntan siempre a la misma base que la API.

```bash
cd backend
python -m app.core.db_migrations            # upgrade a head
python -m app.core.db_migrations --revision 0001
alembic current                             # revisión aplicada
alembic upgrade head --sql                  # SQL sin conectar
```

### Bases creadas por 0.1.0

0.1.0 creaba las tablas con `Base.metadata.create_all()` y no tenía
`alembic_version`. `ensure_schema()` detecta ese caso (`legacy`), hace
`alembic stamp 0001` y después `upgrade head`, sin recrear ni borrar datos.

| Estado | Significado | Acción |
|---|---|---|
| `empty` | sin tablas | `upgrade head` |
| `legacy` | tablas del escáner, sin `alembic_version` | `stamp 0001` + `upgrade head` |
| `managed` | `alembic_version` presente | `upgrade head` |

### Contenedores

`backend/docker-entrypoint.sh` ejecuta `python -m app.core.db_migrations` antes
de arrancar Uvicorn (solo el servicio `backend`; `celery` y `beat` lo asumen).
En producción `AUTO_CREATE_SCHEMA=false`; el `create_all` de arranque queda para
desarrollo local y pruebas.

### Añadir una migración

```bash
cd backend
alembic revision --autogenerate -m "add asset tags"
# revisar SIEMPRE el diff generado y ajustar downgrade()
alembic upgrade head
```

Reglas: una revisión lineal (un único head), `downgrade()` funcional y enums
nativos de PostgreSQL recreados/eliminados en `upgrade`/`downgrade`.

## 2. Backup y restore

```bash
cd backend
python -m app.core.backup backup  --output backups/2026-11-21.dump
python -m app.core.backup restore --input backups/2026-11-21.dump
# o con otra base:
python -m app.core.backup backup --url "postgresql+psycopg2://..." --output ...
```

| Backend | Mecanismo | Notas |
|---|---|---|
| SQLite | API online `sqlite3.backup` | seguro con la app en marcha; no admite `:memory:` |
| PostgreSQL | `pg_dump --format=custom` / `pg_restore --clean --if-exists` | requiere el cliente; la contraseña viaja en `PGPASSWORD`, nunca en `argv` |

`restore` **reemplaza** los objetos existentes. Programa backups fuera del
horario de escaneos y verifica el resultado con un restore en una base de
prueba (ensayo de restore).

## 3. Retención

- `DATA_RETENTION_DAYS` (por defecto `30`; `0` desactiva la purga).
- La tarea `app.tasks.purge_expired_scans_task` corre a diario vía Celery Beat.
- Solo se borran scans en estado terminal (`completed`, `failed`, `cancelled`);
  un scan `pending`/`running` nunca se elimina.
- Se borran explícitamente `ports` y `scan_results` porque SQLite no aplica
  claves foráneas por defecto.

## 4. Verificación

```bash
cd backend
PYTHONPATH=. DATABASE_URL=sqlite:///:memory: pytest tests/core/test_migrations.py tests/core/test_backup.py tests/core/test_retention.py -q
```

Las pruebas cubren: baseline = esquema ORM, reversibilidad, adopción de bases
`create_all`, idempotencia, round-trip SQLite, argumentos de PostgreSQL sin
credenciales en `argv`, purga con hijos y respeto a scans en curso.
