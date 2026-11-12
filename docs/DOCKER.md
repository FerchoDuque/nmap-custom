# Docker Deployment Guide

## Quick Start

### Production Deployment

```bash
# Build and start all services
make prod

# Or manually:
docker-compose build
docker-compose up -d

# View logs
make logs

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

### Development Environment

```bash
# Build and start development services
make dev

# Or manually:
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up

# Frontend will be at: http://localhost:5173
# Backend will be at: http://localhost:8000
```

## Architecture

The application consists of 5 Docker containers:

1. **frontend** - Nginx serving React production build
2. **backend** - FastAPI application with Uvicorn
3. **celery** - Background task processor for scans
4. **redis** - Message broker and cache
5. **db** - PostgreSQL database

## Container Details

### Frontend Container
- **Base**: nginx:alpine
- **Port**: 80
- **Features**:
  - Serves React production build
  - Proxies `/api` to backend
  - Proxies `/ws` for WebSocket
  - Gzip compression
  - Security headers

### Backend Container
- **Base**: python:3.11-slim
- **Port**: 8000
- **Capabilities**: NET_RAW, NET_ADMIN (for SYN scans)
- **Features**:
  - FastAPI with Uvicorn
  - Automatic database migrations
  - Health checks
  - nmap and libpcap installed

### Celery Worker Container
- **Base**: python:3.11-slim (same as backend)
- **Capabilities**: NET_RAW, NET_ADMIN
- **Features**:
  - Processes scan tasks asynchronously
  - Connects to Redis and PostgreSQL
  - Auto-restart on failure

### Redis Container
- **Base**: redis:7-alpine
- **Port**: 6379 (internal)
- **Features**:
  - Persistence with AOF
  - Health checks

### PostgreSQL Container
- **Base**: postgres:15-alpine
- **Port**: 5432 (internal, exposed in dev)
- **Features**:
  - Persistent volume
  - Health checks
  - Automatic initialization

## Networking

All containers communicate through a custom bridge network: `scanner-network`

- Frontend → Backend (HTTP/WebSocket)
- Backend → Database (PostgreSQL)
- Backend → Redis
- Celery → Database
- Celery → Redis

Only the frontend (port 80) is exposed to the host in production.

## Volumes

### Production
- `postgres_data` - PostgreSQL data
- `redis_data` - Redis persistence

### Development
- `postgres_data_dev` - PostgreSQL data
- `redis_data_dev` - Redis persistence
- Source code mounted for hot reload

## Environment Variables

See `.env.docker` for all available environment variables.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_HOST` - Redis hostname
- `CELERY_BROKER_URL` - Celery broker URL
- `CORS_ORIGINS` - Allowed CORS origins

## Common Commands

```bash
# Build containers
make build

# Start services
make up

# Stop services
make down

# View logs
make logs
make logs-backend
make logs-celery

# Access container shells
make shell-backend
make shell-db
make shell-redis

# Run migrations
make migrate

# Run tests
make test

# Clean everything
make clean
```

## Security Considerations

### Privileged Capabilities

The backend and Celery containers require `CAP_NET_RAW` and `CAP_NET_ADMIN` for:
- SYN stealth scans
- Raw socket operations
- OS fingerprinting

**Security implications**:
- Containers can manipulate network packets
- Increased attack surface if compromised
- Use only on trusted networks

**Alternative**: Remove capabilities for TCP-only scanning (less privileged).

### Network Isolation

- Backend, database, and Redis are not directly accessible from host
- Only frontend is exposed
- Use reverse proxy (Nginx, Traefik) for HTTPS in production

## Production Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ RAM
- 10GB+ disk space

### Steps

1. **Clone repository**
```bash
git clone <repository>
cd nmap-custom
```

2. **Configure environment**
```bash
cp .env.docker .env
# Edit .env with production values
```

3. **Build and start**
```bash
docker-compose build
docker-compose up -d
```

4. **Verify deployment**
```bash
docker-compose ps
curl http://localhost/api/health
```

5. **View logs**
```bash
docker-compose logs -f
```

### HTTPS Setup

Use a reverse proxy like Nginx or Traefik:

```yaml
# Example with Traefik
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.scanner.rule=Host(`scanner.yourdomain.com`)"
  - "traefik.http.routers.scanner.tls.certresolver=letsencrypt"
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs <service-name>

# Check container status
docker-compose ps
```

### Database connection errors
```bash
# Verify database is healthy
docker-compose exec db pg_isready -U scanner

# Check connection from backend
docker-compose exec backend python -c "from app.database import engine; print(engine.url)"
```

### Permission errors for scans
```bash
# Verify capabilities
docker inspect scanner-backend | grep -A 10 CapAdd

# Should show: NET_RAW, NET_ADMIN
```

### Frontend can't reach backend
```bash
# Check nginx config
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# Verify backend is accessible
docker-compose exec frontend wget -O- http://backend:8000/api/health
```

## Scaling

### Horizontal Scaling

Scale Celery workers:
```bash
docker-compose up -d --scale celery=3
```

### Resource Limits

Add to docker-compose.yml:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          memory: 512M
```

## Backup & Restore

### Backup Database
```bash
docker-compose exec db pg_dump -U scanner network_scanner > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker-compose exec -T db psql -U scanner network_scanner
```

## Monitoring

### Health Checks
```bash
# Check all services
curl http://localhost/api/health

# Check individual containers
docker-compose ps
```

### Resource Usage
```bash
make stats
# or
docker stats
```

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

## Development Workflow

1. **Start development environment**
```bash
make dev
```

2. **Make code changes**
   - Backend: Changes auto-reload
   - Frontend: Vite hot module replacement

3. **Run tests**
```bash
make test
```

4. **Access services**
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000
   - Database: localhost:5432
   - Redis: localhost:6379

5. **Stop when done**
```bash
make down-dev
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Docker Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build containers
        run: docker-compose build
      - name: Run tests
        run: docker-compose run backend pytest
```

## Migration from Local Development

If you were running locally without Docker:

1. **Export existing data** (if using SQLite)
```bash
# Backup scans
python -c "from app.database import SessionLocal; from app.models import Scan; db = SessionLocal(); scans = db.query(Scan).all(); print(scans)"
```

2. **Start Docker environment**
```bash
make prod
```

3. **Import data** (if needed)
   - Use API to recreate scans
   - Or write migration script

## Legal Notice

This tool is for authorized network scanning only. Ensure you have proper permissions before scanning any network.
