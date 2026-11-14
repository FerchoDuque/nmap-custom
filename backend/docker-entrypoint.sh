#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."

# Wait for PostgreSQL using Python/SQLAlchemy URL parsing (supports the
# `postgresql+psycopg2://` dialect suffix that psycopg2 cannot parse).
python << END
import time
import os

import psycopg2
from sqlalchemy.engine import make_url

database_url = os.environ.get("DATABASE_URL", "")
url = make_url(database_url)

if url.get_backend_name() != "postgresql":
    print(f"Non-PostgreSQL backend ({url.get_backend_name()}); skipping readiness check")
else:
    conninfo = url.set(drivername="postgresql").render_as_string(hide_password=False)
    max_attempts = 30
    for attempt in range(1, max_attempts + 1):
        try:
            conn = psycopg2.connect(conninfo)
            conn.close()
            print("PostgreSQL is up!")
            break
        except Exception as exc:
            print(
                f"PostgreSQL is unavailable (attempt {attempt}/{max_attempts}): "
                f"{type(exc).__name__}"
            )
            time.sleep(1)
    else:
        print("Could not connect to PostgreSQL after 30 attempts")
        raise SystemExit(1)
END

echo "PostgreSQL is ready - executing command"

# Run database migrations
echo "Running database migrations..."
python -c "from app.database import init_db; init_db()" || echo "Database initialization complete"

# Execute the main command
exec "$@"
