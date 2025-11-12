# Docker Deployment Guide

This guide explains how to run the Checkpoint3 application using Docker Compose.

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

### One-Command Startup

```bash
docker-compose up
```

Or run in detached mode (background):

```bash
docker-compose up -d
```

The application will be available at: **http://localhost:5000**

## Using the Makefile (Recommended)

For convenience, use the provided Makefile:

```bash
# Show all available commands
make help

# Build and start services
make up

# View logs
make logs

# Run tests
make test

# Open shell in container
make shell

# Stop services
make down
```

## Manual Docker Commands

### Build Images
```bash
docker-compose build
```

### Start Services
```bash
docker-compose up
```

### Start in Background
```bash
docker-compose up -d
```

### View Logs
```bash
# All services
docker-compose logs -f

# Web service only
docker-compose logs -f web

# Worker service only
docker-compose logs -f worker
```

### Stop Services
```bash
docker-compose down
```

### Remove Everything (including volumes)
```bash
docker-compose down -v
```

## Services

The docker-compose setup includes:

1. **web** - Main Flask application (port 5000)
2. **worker** - Background worker for partner ingest queue

## Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Then edit `.env` to customize:

```env
APP_SECRET_KEY=your-secret-key-here
FLASK_ENV=development
PORT=5000
SEED_DATA=false
```

## Database

The SQLite database is stored in a Docker volume (`db-data`) for persistence.

### Access Database
```bash
# Open SQLite shell
docker-compose exec web sqlite3 /app/data/app.sqlite

# Or using make
make shell-db
```

### Seed Database
```bash
docker-compose exec web python src/seed.py

# Or using make
make seed
```

### Run Migrations
```bash
docker-compose exec web python scripts/run_migrations.py

# Or using make
make migrate
```

## Running Tests

```bash
# Run all tests
docker-compose exec web python -m pytest -v

# Run with coverage
docker-compose exec web python -m pytest --cov=src --cov-report=html

# Or using make
make test
make test-coverage
```

## Health Checks

The application provides health endpoints:

```bash
# Basic health check
curl http://localhost:5000/health

# Readiness check (includes database connectivity)
curl http://localhost:5000/ready

# Or using make
make health
make ready
```

## Development Workflow

For development with live code reloading:

1. Start services:
   ```bash
   make up
   ```

2. View logs:
   ```bash
   make logs
   ```

3. Make code changes - they'll be reflected automatically (volumes are mounted)

4. Run tests:
   ```bash
   make test
   ```

5. Access shell if needed:
   ```bash
   make shell
   ```

## Production Deployment

For production:

1. Update `.env` with secure values:
   ```env
   APP_SECRET_KEY=<strong-random-key>
   FLASK_ENV=production
   ```

2. Comment out volume mounts in `docker-compose.yml` (or use a production override)

3. Build and start:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

## Troubleshooting

### Port Already in Use
If port 5000 is already in use, change it in `.env`:
```env
PORT=8000
```

And update the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8000:8000"
```

### Database Locked
If you get "database is locked" errors:
```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Rebuild and start
docker-compose up --build
```

### View Container Logs
```bash
# All containers
docker-compose logs

# Specific container
docker-compose logs web
docker-compose logs worker

# Follow logs
docker-compose logs -f
```

### Exec into Container
```bash
docker-compose exec web /bin/bash
```

### Check Service Status
```bash
docker-compose ps

# Or using make
make status
```

### Reset Everything
```bash
# Stop and remove everything
make clean

# Rebuild from scratch
make rebuild
```

## Architecture

```
┌─────────────────────────────────────┐
│     Docker Host                     │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │   web        │  │   worker    │ │
│  │   (Flask)    │  │   (Queue)   │ │
│  │   :5000      │  │             │ │
│  └──────┬───────┘  └──────┬──────┘ │
│         │                 │        │
│         └────────┬────────┘        │
│                  │                 │
│         ┌────────▼────────┐        │
│         │   db-data       │        │
│         │   (SQLite)      │        │
│         └─────────────────┘        │
└─────────────────────────────────────┘
```

## Next Steps

1. Start the application: `make up`
2. Access http://localhost:5000
3. Register a user account
4. Add products to cart
5. Complete checkout
6. View receipt

For API documentation and advanced features, see the main [README.md](../README.md).
