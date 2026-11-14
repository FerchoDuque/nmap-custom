# Network Scanner Backend

## Setup

### Docker (Recommended)

See main [Docker Documentation](../docs/DOCKER.md) for complete instructions.

Quick start:
```bash
# From project root
docker-compose up -d backend celery
```

### Local Development

#### Prerequisites
- Python 3.11+
- Redis server

### Installation

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
copy .env.example .env
# Edit .env with your configuration
```

4. Initialize database:
```bash
python -c "from app.database import init_db; init_db()"
```

### Running the Application

1. Start Redis server:
```bash
redis-server
```

2. Start Celery worker:
```bash
celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
```

3. Start FastAPI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Running Tests

```bash
pytest tests/ -v --cov=app
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   ├── celery_app.py        # Celery configuration
│   ├── tasks.py             # Celery tasks
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── api/                 # API routes
│   ├── core/                # Core scanning logic
│   └── utils/               # Utilities
├── tests/                   # Tests
├── requirements.txt
└── pyproject.toml
```

## Legal Notice

This tool is intended for use on LOCAL NETWORKS ONLY. Scanning networks without proper authorization is illegal. Use responsibly.
