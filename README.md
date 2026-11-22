# Network Scanner - Advanced Nmap-Style Tool

[![CI](https://github.com/FerchoDuque/nmap-custom/actions/workflows/ci.yml/badge.svg)](https://github.com/FerchoDuque/nmap-custom/actions/workflows/ci.yml)
[![CodeQL](https://github.com/FerchoDuque/nmap-custom/actions/workflows/codeql.yml/badge.svg)](https://github.com/FerchoDuque/nmap-custom/actions/workflows/codeql.yml)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)

A comprehensive network scanning tool with Python/FastAPI backend and React/TypeScript frontend, designed for local network analysis and security assessment.

## ⚠️ Legal Disclaimer

**This tool is intended for use on LOCAL NETWORKS ONLY.** Scanning networks without proper authorization is illegal and unethical. Use this tool responsibly and only on networks you own or have explicit written permission to scan.

## 🚀 Features

### Backend (Python/FastAPI)
- **Multiple Scan Types**: TCP Connect, SYN Stealth, UDP, and Comprehensive scans
- **Service Detection**: Banner grabbing and version identification
- **OS Fingerprinting**: Operating system detection using nmap and heuristics
- **Network Discovery**: Host discovery and topology mapping
- **Real-time Updates**: WebSocket support for live scan progress
- **Scheduled Scans**: Automated scanning with cron expressions
- **Export Formats**: JSON, XML (nmap-style), and CSV
- **Async Processing**: Celery + Redis for background task execution

### Frontend (React/TypeScript)
- **Modern UI**: Material-UI dark theme with responsive design
- **Real-time Monitoring**: Live scan progress via WebSocket
- **Network Visualization**: Interactive topology graphs with D3.js
- **Results Management**: Filterable tables with export functionality
- **Schedule Management**: Create and manage automated scans
- **Type Safety**: Full TypeScript implementation

## 📋 Prerequisites

- **Docker** 20.10+
- **Docker Compose** 2.0+
- 2GB+ RAM
- 10GB+ disk space

*For local development without Docker:*
- Python 3.11+
- Node.js 18+
- Redis
- PostgreSQL (or SQLite)

## 🛠️ Installation & Quick Start

### Docker Deployment (Recommended)

**Production:**
```bash
# Clone repository
git clone https://github.com/FerchoDuque/nmap-custom.git
cd nmap-custom

# Build and start all services
make prod

# Or manually:
docker compose build
docker compose up -d
```

**Development:**
```bash
# Build and start with hot reload
make dev

# Or manually:
docker compose -f docker-compose.dev.yml up
```

**Access the application:**
- **Frontend**: http://localhost (production) or http://localhost:5173 (dev)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs

**Common commands:**
```bash
make logs          # View all logs
make logs-backend  # View backend logs
make shell-backend # Access backend shell
make migrate       # Run database migrations
make test          # Run tests
make check         # Local lint/type/tests (no Docker)
make verify        # Full local checks incl. frontend build
make down          # Stop all services
```

See [Docker Documentation](docs/DOCKER.md) for detailed information.

### Local Development (Without Docker)

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install dependencies (lockfile único `uv.lock`):
```bash
pip install uv==0.10.9
uv sync --extra dev
```

4. Configure environment:
```bash
copy .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
python -c "from app.database import init_db; init_db()"
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment:
```bash
copy .env.example .env
```

## 🚀 Running the Application

### Start Backend Services

1. **Start Redis** (in a separate terminal):
```bash
redis-server
```

2. **Start Celery Worker** (in a separate terminal):
```bash
cd backend
celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
```

3. **Start FastAPI Server** (in a separate terminal):
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend

```bash
cd frontend
npm run dev
```

The application will be available at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs

## 📁 Project Structure

```
nmap-custom/
├── backend/                 # Python/FastAPI backend
│   ├── app/
│   │   ├── api/             # REST API routes
│   │   ├── core/            # Scanning engine
│   │   ├── models/          # Database models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── main.py          # FastAPI app
│   │   ├── tasks.py         # Celery tasks
│   │   └── config.py        # Configuration
│   ├── tests/               # Backend tests
│   └── uv.lock              # Lockfile (fuente de verdad de dependencias)
├── frontend/                # React/TypeScript frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API clients
│   │   ├── store/           # State management
│   │   ├── types/           # TypeScript types
│   │   └── App.tsx
│   └── package.json
├── electron/                # Aplazado (ver DEC-014); sin entregable en 0.1.0
└── docs/                    # Documentation
```

## 🔧 Configuration

### Backend (.env)
```env
DATABASE_URL=sqlite:///./network_scanner.db
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
API_HOST=0.0.0.0
API_PORT=8000
# Resource limits and resilience
MAX_HOSTS_PER_SCAN=1024
MAX_PORTS_PER_SCAN=65535
DEFAULT_SCAN_TIMEOUT=300
RESOLVE_HOSTNAMES=true
LOG_LEVEL=INFO
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints

- `POST /api/scans` - Create new scan
- `GET /api/scans` - List all scans
- `GET /api/scans/{id}` - Get scan details
- `POST /api/scans/{id}/export` - Export results
- `WS /ws/scan/{id}` - WebSocket for real-time updates
- `POST /api/schedules` - Create scheduled scan
- `GET /api/health` - Liveness + database connectivity (`503` when degraded)
- `GET /api/metrics` - Scan counts and totals for dashboards

See [Observability](docs/OBSERVABILITY.md) for JSON log fields, health
semantics and metrics, and [CI](docs/CI.md) for the reproducible checks.

## 🧪 Testing

### Reproducible checks (recommended)

Run the full quality gate locally (no Docker/network required):

```powershell
# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1
```

```bash
# Linux/macOS/WSL
bash scripts/verify.sh
```

Add `-SkipBuild`/`--skip-build` to skip the frontend build, or use `make check`
(no build) / `make verify` (with build). CI runs the same checks; see
[CI documentation](docs/CI.md).

### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests
```bash
cd frontend
npm run test:run
npm run typecheck
```

## 🎯 Usage Examples

### Quick Scan
1. Open the frontend at http://localhost:5173
2. Click "New Scan"
3. Enter target (e.g., `192.168.1.0/24`)
4. Select scan type (TCP Connect recommended for beginners)
5. Click "Start Scan"

### Scheduled Scan
1. Navigate to "Schedules"
2. Click "New Schedule"
3. Configure scan parameters
4. Set cron expression (e.g., `0 2 * * *` for daily at 2 AM)
5. Save schedule

## 🔐 Security Considerations

- **Authorization**: Only scan networks you own or have explicit written permission to test. Validation is syntactic and does not replace authorization controls.
- **Privileges**: SYN scans and OS fingerprinting require root/administrator privileges; run the worker with `NET_RAW`/`NET_ADMIN` only, never privileged mode.
- **Resource limits**: `MAX_HOSTS_PER_SCAN` (default `1024`) and `MAX_PORTS_PER_SCAN` (default `65535`) cap scan size; oversized CIDR ranges/port lists are rejected with `422` instead of being truncated.
- **Timeouts**: `DEFAULT_SCAN_TIMEOUT` (default `300` s) bounds each scan; an exceeded scan is marked `failed` with a safe message instead of hanging a worker.
- **Undisclosed errors**: unhandled exceptions return `{"detail": "Internal server error"}`; details stay in structured logs.
- **Reverse DNS**: `RESOLVE_HOSTNAMES=false` skips reverse lookups (useful without DNS/for deterministic tests); lookup failures are ignored.
- **CORS**: `CORS_ORIGINS` must contain explicit origins; `*` and empty lists are rejected at startup.
- **Secrets**: replace the placeholder `SECRET_KEY` before any non-local deployment. In `ENV=production` the API logs a warning if the default is still in use.
- **Firewall**: May trigger IDS/IPS systems
- **Rate Limiting**: Aggressive scans can impact network performance
- **Legal**: Only scan networks you own or have permission to test

See [`docs/RUNBOOK.md`](docs/RUNBOOK.md) for incident procedures and
[`docs/RELEASE.md`](docs/RELEASE.md) for the release checklist. Report
vulnerabilities privately following [`SECURITY.md`](SECURITY.md).

## 📖 Documentation

| Documento | Contenido |
|---|---|
| [`CHANGELOG.md`](CHANGELOG.md) | Historial de cambios por release |
| [`docs/CONTRACT.md`](docs/CONTRACT.md) | Contrato REST/WS v1.0, validación, errores y operación |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Operación, diagnóstico por síntoma y recuperación |
| [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md) | Logs JSON, health y métricas |
| [`docs/RELEASE.md`](docs/RELEASE.md) | Checklist de release, smoke tests y rollback |
| [`docs/CI.md`](docs/CI.md) | Verificación local y GitHub Actions |
| [`docs/DOCKER.md`](docs/DOCKER.md) | Contenedores, capacidades, backups y troubleshooting |
| [`docs/UI.md`](docs/UI.md) | Dirección visual y convenciones del frontend |

## 🛣️ Roadmap

### 0.1.0 — publicado (2026-11-14)

- [x] Motor de escaneo (TCP connect/SYN/UDP/comprehensive), detección de servicios y OS fingerprint.
- [x] API REST + WebSocket con contrato v1.0, schedules y exportación.
- [x] Frontend React/TypeScript con progreso en vivo.
- [x] Observabilidad (logs JSON, `/api/health`, `/api/metrics`) y resiliencia.
- [x] Dry-run de release, compose healthy y tag `v0.1.0`.

### 0.2.0 — en curso

- [ ] CI con checks obligatorios, CodeQL y Dependabot.
- [ ] Licencia, guía de contribución y política de seguridad.
- [ ] Migraciones Alembic y backups automatizados.
- [ ] Autenticación, RBAC y audit log.
- [ ] Allowlist de alcance y cuotas por cliente.
- [ ] E2E determinista en red Docker aislada (smoke 3–10).

### Futuro

- [ ] Perfiles de escaneo, diff entre scans e inventario de activos.
- [ ] Notificaciones e informes programados.
- [ ] Exportador Prometheus/OpenTelemetry.
- [ ] Empaquetado desktop (DEC-014).

## 🤝 Contributing

Lee [`CONTRIBUTING.md`](CONTRIBUTING.md) (TDD, verificación y checklist de PR) y el
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Los cambios entran por PR con CI en
verde.

## 📄 License

[GNU GPL v3.0](LICENSE). Se eligió GPL-3.0 porque `python-nmap` (dependencia de
la detección de SO) es GPL-3.0; ver DEC-016 en [`decisions.md`](decisions.md).
Uso permitido únicamente en redes propias o con autorización explícita.

## 🙏 Acknowledgments

- **nmap** - Network scanning inspiration
- **FastAPI** - Modern Python web framework
- **Material-UI** - React component library
- **Scapy** - Packet manipulation library

---

**Remember**: Always obtain proper authorization before scanning any network. Unauthorized network scanning is illegal.
