# Network Scanner - Advanced Nmap-Style Tool

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
git clone <repository>
cd nmap-custom

# Build and start all services
make prod

# Or manually:
docker-compose build
docker-compose up -d
```

**Development:**
```bash
# Build and start with hot reload
make dev

# Or manually:
docker-compose -f docker-compose.dev.yml up
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

3. Install dependencies:
```bash
pip install -r requirements.txt
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
celery -A app.celery_app worker --loglevel=info --pool=solo
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
│   └── requirements.txt
├── frontend/                # React/TypeScript frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API clients
│   │   ├── store/           # State management
│   │   ├── types/           # TypeScript types
│   │   └── App.tsx
│   └── package.json
├── electron/                # Electron desktop app (future)
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

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests
```bash
cd frontend
npm run test
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

- **Privileges**: SYN scans and OS fingerprinting require root/administrator privileges
- **Firewall**: May trigger IDS/IPS systems
- **Rate Limiting**: Aggressive scans can impact network performance
- **Legal**: Only scan networks you own or have permission to test

## 🛣️ Roadmap

- [x] Core scanning engine
- [x] FastAPI backend
- [x] React frontend foundation
- [ ] Complete UI components (ScanConfig, NetworkTopology, etc.)
- [ ] Electron desktop packaging
- [ ] Advanced network visualization
- [ ] Vulnerability detection integration
- [ ] Report generation
- [ ] Multi-user support with authentication

## 🤝 Contributing

This is a personal project for educational purposes. Feel free to fork and adapt for your own use.

## 📄 License

This project is for educational and authorized security testing purposes only. Use responsibly.

## 🙏 Acknowledgments

- **nmap** - Network scanning inspiration
- **FastAPI** - Modern Python web framework
- **Material-UI** - React component library
- **Scapy** - Packet manipulation library

---

**Remember**: Always obtain proper authorization before scanning any network. Unauthorized network scanning is illegal.
