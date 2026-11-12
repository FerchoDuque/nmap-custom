# Network Scanner - Docker Quick Reference

## Quick Start Commands

### Production
```bash
make prod          # Build and start
make logs          # View logs
make down          # Stop all
```

### Development
```bash
make dev           # Build and start with hot reload
make logs-backend  # View backend logs
make shell-backend # Access backend shell
make test          # Run tests
```

## Services

| Service  | Port | Description |
|----------|------|-------------|
| frontend | 80   | React UI with Nginx |
| backend  | 8000 | FastAPI API |
| db       | 5432 | PostgreSQL (internal) |
| redis    | 6379 | Redis (internal) |
| celery   | -    | Background worker |

## Architecture

```
User → Frontend (Nginx:80)
       ↓
       Backend (FastAPI:8000) ← Celery Worker
       ↓                        ↓
       PostgreSQL              Redis
```

## Environment Variables

Key variables in `.env.docker`:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_HOST` - Redis hostname
- `CELERY_BROKER_URL` - Celery broker
- `CORS_ORIGINS` - Allowed origins
- `SECRET_KEY` - **Change in production!**

## Common Tasks

### View Logs
```bash
make logs              # All services
make logs-backend      # Backend only
make logs-celery       # Celery only
```

### Database
```bash
make shell-db          # PostgreSQL shell
make migrate           # Run migrations
```

### Development
```bash
make shell-backend     # Backend shell
make test              # Run tests
make restart-backend   # Restart backend
```

### Cleanup
```bash
make down              # Stop services
make clean             # Remove everything
```

## Troubleshooting

### Services won't start
```bash
docker-compose ps      # Check status
docker-compose logs    # Check logs
```

### Database connection errors
```bash
docker-compose exec db pg_isready -U scanner
```

### Permission errors
```bash
# Verify NET_RAW capability
docker inspect scanner-backend | grep CapAdd
```

## Security Notes

⚠️ **Privileged Capabilities**: Backend and Celery containers have `NET_RAW` and `NET_ADMIN` for network scanning.

⚠️ **Production**: Change `SECRET_KEY` in `.env.docker`

⚠️ **Legal**: Only scan authorized networks

## Full Documentation

See [docs/DOCKER.md](docs/DOCKER.md) for complete documentation.
