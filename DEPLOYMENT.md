# SkillPM Deployment Guide

## Overview

This guide covers deploying SkillPM Registry API to production.

## Prerequisites

- Python 3.9+ (3.11+ recommended)
- PostgreSQL 12+ (or SQLite for small deployments)
- Docker (for containerized deployment)
- GitHub account (for OAuth if using)
- Domain name (for HTTPS)

## Environment Setup

### 1. Create Production Environment File

Create `.env.production`:

```bash
# Environment
ENV=production
DEBUG=false

# Logging
LOG_LEVEL=INFO

# CORS - CRITICAL: Set to your domains only
CORS_ORIGINS=https://skillpm.dev,https://app.skillpm.dev,https://api.skillpm.dev

# Database
DATABASE_URL=postgresql://user:password@db.skillpm.dev:5432/skillpm
# OR for SQLite (not recommended for production)
# DATABASE_URL=sqlite:///skillpm.db

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_WORKERS=4

# Request limits
MAX_BODY_SIZE=5000000  # 5MB

# Rate limiting
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_WINDOW=60

# Secrets
SECRET_KEY=your-secret-key-here  # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"

# API Keys
API_KEY_PREFIX=skpm_
API_KEY_EXPIRATION_DAYS=365  # Optional: if implementing expiration
```

### 2. Database Setup

#### PostgreSQL (Recommended)

```bash
# Create database
createdb skillpm

# Create user
createuser skillpm_user
psql -c "ALTER USER skillpm_user WITH PASSWORD 'secure_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE skillpm TO skillpm_user;"

# Initialize schema
cd registry
alembic upgrade head
cd ..
```

#### SQLite (Simple but not recommended for production)

```bash
cd registry
python -c "from db.connection import init_db; init_db()"
cd ..
```

## Deployment Options

### Option A: Docker Container (Recommended)

#### 1. Build Image

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY registry/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY registry/ .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and push:

```bash
docker build -t skillpm:latest .
docker tag skillpm:latest registry.example.com/skillpm:latest
docker push registry.example.com/skillpm:latest
```

#### 2. Run Container

```bash
docker run -d \
  --name skillpm \
  --restart unless-stopped \
  -p 8000:8000 \
  -e ENV=production \
  -e CORS_ORIGINS=https://skillpm.dev \
  -e DATABASE_URL=postgresql://user:pass@db:5432/skillpm \
  --health-cmd="curl -f http://localhost:8000/health" \
  --health-interval=30s \
  registry.example.com/skillpm:latest
```

#### 3. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    image: registry.example.com/skillpm:latest
    ports:
      - "8000:8000"
    environment:
      ENV: production
      LOG_LEVEL: INFO
      CORS_ORIGINS: https://skillpm.dev
      DATABASE_URL: postgresql://skillpm:password@db:5432/skillpm
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: skillpm
      POSTGRES_USER: skillpm
      POSTGRES_PASSWORD: change_me
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U skillpm"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

Deploy with:

```bash
docker-compose up -d
docker-compose logs -f api
```

### Option B: Manual Installation

#### 1. Install Python Packages

```bash
cd registry
pip install -r requirements.txt
cd ..
```

#### 2. Initialize Database

```bash
cd registry
alembic upgrade head
cd ..
```

#### 3. Run with Gunicorn

```bash
cd registry
gunicorn \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  main:app
```

#### 4. Use Systemd for Auto-Start

Create `/etc/systemd/system/skillpm.service`:

```ini
[Unit]
Description=SkillPM Registry API
After=network.target postgresql.service

[Service]
Type=notify
User=skillpm
WorkingDirectory=/opt/skillpm
ExecStart=/opt/skillpm/venv/bin/gunicorn \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  registry.main:app
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable skillpm
sudo systemctl start skillpm
```

## Reverse Proxy Setup

### Nginx Configuration

```nginx
upstream skillpm {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.skillpm.dev;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.skillpm.dev;

    ssl_certificate /etc/letsencrypt/live/api.skillpm.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.skillpm.dev/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/skillpm_access.log;
    error_log /var/log/nginx/skillpm_error.log;

    # Proxy settings
    location / {
        proxy_pass http://skillpm;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=50 nodelay;
}
```

## Monitoring & Logging

### Health Checks

```bash
# Check API health
curl https://api.skillpm.dev/health

# Expected response:
# {"status": "healthy"}
```

### Logging

Configure centralized logging:

```bash
# Journalctl (if using Systemd)
journalctl -u skillpm -f

# Container logs
docker-compose logs -f api
```

### Metrics (Optional - Phase 3)

Add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('skillpm_requests_total', 'Total requests')
request_duration = Histogram('skillpm_request_duration_seconds', 'Request duration')

@app.get("/metrics")
def metrics():
    return generate_latest()
```

## Backup & Recovery

### Database Backup

#### PostgreSQL

```bash
# Backup
pg_dump -U skillpm -h db.skillpm.dev skillpm > skillpm_backup.sql

# Restore
psql -U skillpm -h db.skillpm.dev skillpm < skillpm_backup.sql
```

#### Automated Backups

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d)
pg_dump -U skillpm skillpm | gzip > /backups/skillpm_$DATE.sql.gz

# Keep only last 30 days
find /backups -name "skillpm_*.sql.gz" -mtime +30 -delete
```

Schedule with cron:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/skillpm/backup.sh
```

### Database Recovery

```bash
# Check backup
pg_restore --list skillpm_backup.sql | head

# Restore
pg_restore -U skillpm -d skillpm skillpm_backup.sql
```

## Security Hardening

### 1. HTTPS/TLS

```bash
# Using Let's Encrypt with Certbot
sudo certbot certonly --standalone -d api.skillpm.dev

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### 2. Firewall

```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 3. Database Security

```bash
# Create limited user for API
psql -c "CREATE USER skillpm_api WITH PASSWORD 'strong_password';"
psql -c "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO skillpm_api;"
```

### 4. Rate Limiting (per-user, built-in)

Already configured in the code. No additional setup needed.

### 5. API Key Rotation

Users can rotate keys via:

```bash
curl -X POST https://api.skillpm.dev/api/v1/authors/me/rotate-key \
  -H "Authorization: Bearer $OLD_KEY"
```

## Performance Tuning

### Database Connection Pool

Configured in `registry/db/connection.py`:

```python
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,      # Connections to keep open
    max_overflow=40,   # Extra connections if needed
    pool_recycle=3600, # Recycle connections after 1 hour
)
```

### Nginx Caching

```nginx
# Cache GET requests for 5 minutes
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=skillpm:10m;

location / {
    proxy_cache skillpm;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
}
```

### Query Optimization

Use database indexes (automatically created):

```bash
# Check indexes
psql skillpm -c "\d+ skills"

# Monitor slow queries
psql skillpm -c "SET log_statement = 'all';"
```

## Maintenance

### Regular Tasks

#### Daily
- Check health: `curl https://api.skillpm.dev/health`
- Review logs for errors
- Monitor disk space

#### Weekly
- Review metrics/stats
- Check backup success
- Test database recovery

#### Monthly
- Review and rotate old logs
- Check security updates available
- Performance profiling

#### Quarterly
- Load testing
- Security audit
- Database maintenance (VACUUM, ANALYZE)

### Zero-Downtime Updates

```bash
# 1. Pull new code and build
git pull
docker build -t skillpm:v1.1 .

# 2. Run new version on different port
docker run -d -p 8001:8000 skillpm:v1.1

# 3. Test new version
curl http://localhost:8001/health

# 4. Switch Nginx to new port
vim /etc/nginx/sites-available/skillpm
nginx -s reload

# 5. Stop old version
docker stop skillpm
```

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker logs skillpm
# or
journalctl -u skillpm -n 50

# Verify database connection
psql -U skillpm -h db.skillpm.dev skillpm -c "SELECT 1"

# Check port in use
lsof -i :8000
```

### Database Locked

```bash
# Check active connections
psql skillpm -c "SELECT * FROM pg_stat_activity WHERE state != 'idle';"

# Kill long-running query
psql skillpm -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > 300;"
```

### Memory Leak

```bash
# Monitor memory
docker stats skillpm

# Restart service
docker restart skillpm
# or
sudo systemctl restart skillpm
```

## Deployment Checklist

Before going live:

- [ ] Environment variables set
- [ ] Database initialized
- [ ] Backups configured
- [ ] HTTPS/TLS working
- [ ] CORS origins restricted
- [ ] Firewall rules in place
- [ ] Monitoring setup
- [ ] Health checks passing
- [ ] Load test completed
- [ ] Security audit done
- [ ] Team trained on procedures
- [ ] Runbook documented
- [ ] Incident response plan ready

## Rollback Procedure

If something goes wrong:

```bash
# 1. Stop new version
docker stop skillpm

# 2. Downgrade database (if schema changed)
cd registry
alembic downgrade -1
cd ..

# 3. Start old version
docker run -d --name skillpm -p 8000:8000 skillpm:v1.0

# 4. Verify
curl http://localhost:8000/health
```

## Getting Help

- **Logs:** Check application and database logs first
- **Monitoring:** Review metrics and performance data
- **Testing:** Use the test suite to verify functionality
- **Documentation:** Check TESTING.md, MIGRATIONS.md

## Next Steps

1. Choose deployment option (Docker recommended)
2. Set up monitoring
3. Configure backups
4. Deploy to staging
5. Run full test suite
6. Deploy to production
7. Monitor closely first 24 hours

