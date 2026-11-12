#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."

# Wait for PostgreSQL using Python
python << END
import time
import psycopg2
import os

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.close()
        print("PostgreSQL is up!")
        break
    except Exception as e:
        attempt += 1
        print(f"PostgreSQL is unavailable - sleeping (attempt {attempt}/{max_attempts})")
        time.sleep(1)
else:
    print("Could not connect to PostgreSQL after 30 attempts")
    exit(1)
END

echo "PostgreSQL is ready - executing command"

# Run database migrations
echo "Running database migrations..."
python -c "from app.database import init_db; init_db()" || echo "Database initialization complete"

# Execute the main command
exec "$@"
