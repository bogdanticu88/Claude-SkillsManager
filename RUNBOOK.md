# SkillPM Operations Runbook

**Purpose:** Quick reference for common operational tasks

## Quick Links

- [Deployment Guide](./DEPLOYMENT.md)
- [Testing Guide](./TESTING.md)
- [Migrations Guide](./MIGRATIONS.md)
- [Technical Review](./TECHNICAL_REVIEW.md)

---

## Daily Operations

### Health Check (Every 4 hours)

```bash
# API health
curl -I https://api.skillpm.dev/health
# Expected: 200 OK

# Database connection
psql skillpm -c "SELECT NOW();"
# Expected: Current timestamp

# Disk space
df -h /data
# Expected: > 20% free
```

### Monitor Logs

```bash
# Real-time logs
docker logs -f skillpm

# Last 100 lines with errors
docker logs skillpm 2>&1 | grep -i error | tail -100

# By severity
docker logs skillpm 2>&1 | grep ERROR
docker logs skillpm 2>&1 | grep WARNING
```

### Backup Status

```bash
# Last successful backup
ls -lh /backups/skillpm_*.sql.gz | tail -1

# Expected: Today's date in filename
```

---

## Common Issues & Solutions

### Issue: API Returns 500 Errors

**Diagnosis:**

```bash
# Check logs
docker logs skillpm | grep ERROR

# Check database
psql skillpm -c "SELECT 1;"

# Check disk
df -h /
```

**Solutions:**

```bash
# Restart API
docker restart skillpm

# Restart database
docker restart skillpm_db

# Check for disk space
du -sh /data/*
```

### Issue: High Memory Usage

**Diagnosis:**

```bash
# Check memory
docker stats skillpm

# Check for memory leaks
docker exec skillpm ps aux | grep python
```

**Solution:**

```bash
# Graceful restart
docker restart skillpm

# Monitor after restart
watch docker stats skillpm
```

### Issue: Database Connection Errors

**Diagnosis:**

```bash
# Check database is running
docker ps | grep postgres

# Check connection
psql -h db -U skillpm -c "SELECT 1;"

# Check pool
psql skillpm -c "SELECT * FROM pg_stat_activity;"
```

**Solutions:**

```bash
# Restart database
docker restart skillpm_db

# Wait for recovery
sleep 30
curl http://localhost:8000/health

# Increase connection pool if needed
# Edit registry/db/connection.py: pool_size=30
```

### Issue: High API Latency

**Diagnosis:**

```bash
# Check response times
curl -w "Time: %{time_total}s\n" https://api.skillpm.dev/api/v1/skills/

# Check slow queries
psql skillpm -c "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;"

# Check database load
docker stats skillpm_db
```

**Solutions:**

```bash
# Add database indexes
alembic revision --autogenerate -m "add missing indexes"

# Increase workers
# Edit docker-compose: SERVER_WORKERS=8

# Cache frequently accessed data
# Edit registry/services/cache.py: increase TTL
```

### Issue: Rate Limiting Issues

**Diagnosis:**

```bash
# Check logs for rate limit hits
docker logs skillpm | grep "Rate limit"

# Check which users are hitting limits
docker logs skillpm | grep "X-RateLimit"
```

**Solutions:**

```bash
# Increase per-user limit (in .env)
RATE_LIMIT_REQUESTS=300  # Was 200

# Restart
docker restart skillpm

# Or whitelist specific users (implement in middleware)
```

---

## Scheduled Tasks

### Daily (2 AM)

```bash
# Database backup
/opt/skillpm/backup.sh

# Verify
ls -lh /backups/skillpm_$(date +%Y%m%d).sql.gz
```

### Weekly (Sunday 3 AM)

```bash
# Cleanup old logs (keep 30 days)
find /var/log/skillpm -name "*.log" -mtime +30 -delete

# Database maintenance
psql skillpm -c "VACUUM ANALYZE;"
```

### Monthly (1st at 4 AM)

```bash
# Full backup verification
pg_restore --list /backups/skillpm_$(date -d "last day of last month" +%Y%m%d).sql.gz | head

# Log rotation
logrotate -f /etc/logrotate.d/skillpm
```

---

## Deployment Procedures

### Deploy Update (Zero Downtime)

```bash
#!/bin/bash
set -e

echo "1. Pull latest code"
git pull origin main

echo "2. Build new Docker image"
docker build -t skillpm:latest registry/

echo "3. Tag version"
docker tag skillpm:latest registry.example.com/skillpm:$(git rev-parse --short HEAD)

echo "4. Test new image"
docker run --rm skillpm:latest python -m pytest tests/ -x

echo "5. Push to registry"
docker push registry.example.com/skillpm:latest

echo "6. Update service"
docker-compose up -d

echo "7. Health check"
sleep 10
curl http://localhost:8000/health

echo "✓ Deployment complete"
```

### Rollback (If Needed)

```bash
#!/bin/bash
echo "Rolling back to previous version..."

# Stop current version
docker-compose stop api

# Revert code
git revert HEAD --no-edit

# Start previous version
docker-compose up -d api

# Verify
sleep 5
curl http://localhost:8000/health

echo "✓ Rollback complete"
```

---

## Security Operations

### API Key Rotation

```bash
# User rotates their own key via API:
curl -X POST https://api.skillpm.dev/api/v1/authors/me/rotate-key \
  -H "Authorization: Bearer $OLD_KEY"

# Get new key from response
# Distribute to applications using old key
```

### Audit Log Review

```bash
# Review authentication failures
docker logs skillpm | grep "Failed login"

# Review rate limit violations
docker logs skillpm | grep "Rate limit exceeded"

# Review privilege escalations
docker logs skillpm | grep "Admin operation"
```

### Security Update

```bash
# Check for vulnerable dependencies
cd registry
pip install safety
safety check
cd ..

# Update if needed
pip install --upgrade vulnerable-package
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

---

## Database Operations

### Take Manual Backup

```bash
pg_dump skillpm | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore from Backup

```bash
# Warning: This will overwrite current database

# 1. Backup current database first!
pg_dump skillpm | gzip > backup_before_restore.sql.gz

# 2. Restore
gunzip -c skillpm_backup.sql.gz | psql skillpm

# 3. Verify
psql skillpm -c "SELECT COUNT(*) FROM skills;"
```

### Query Performance

```bash
# Enable query logging
psql skillpm -c "SET log_statement = 'all';"

# Find slow queries
psql skillpm -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# Reset stats
psql skillpm -c "SELECT pg_stat_statements_reset();"
```

### Check Database Size

```bash
# Total size
psql skillpm -c "SELECT pg_size_pretty(pg_database_size('skillpm'));"

# Per table
psql skillpm -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

---

## Monitoring & Alerts

### Set Up Monitoring

```bash
# Health check endpoint (built-in)
curl https://api.skillpm.dev/health

# Response:
# {"status": "healthy"}

# Set up monitoring in your tool:
# - Interval: 30 seconds
# - Timeout: 10 seconds
# - Failure threshold: 3
# - Alert: page on-call
```

### Key Metrics to Monitor

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| API Response Time | > 2s | Check database load |
| Error Rate | > 1% | Check logs |
| Disk Space | < 20% | Cleanup or resize |
| Memory Usage | > 80% | Restart API |
| Database Connections | > 90% | Increase pool size |
| CPU Usage | > 80% | Scale up |

### Alerting Examples

```bash
# Nagios/Icinga
check_http -H api.skillpm.dev -u /health -p 443

# Prometheus
- alert: SkillPMDown
  expr: up{job="skillpm"} == 0
  for: 5m
  annotations:
    summary: "SkillPM API is down"
```

---

## Testing in Production

### Health Check Script

```bash
#!/bin/bash
# test_production.sh

echo "Testing SkillPM Production"
echo "=========================="

# API health
echo -n "API Health: "
curl -s http://localhost:8000/health | jq .status

# Database
echo -n "Database: "
psql skillpm -c "SELECT 'OK' as status;" | tail -1

# Disk
echo "Disk Space:"
df -h / | tail -1

# Memory
echo "Memory:"
free -h | tail -1

# API latency
echo -n "API Latency: "
curl -w "%{time_total}s\n" -o /dev/null -s http://localhost:8000/api/v1/skills/
```

Run daily:

```bash
chmod +x test_production.sh
0 6 * * * /opt/skillpm/test_production.sh
```

---

## Emergency Procedures

### If API is Down

```bash
# 1. Check if container is running
docker ps | grep skillpm

# 2. Check logs for crashes
docker logs skillpm | tail -50

# 3. Check system resources
docker stats skillpm

# 4. Restart
docker restart skillpm

# 5. Check health
sleep 10
curl http://localhost:8000/health

# If still down:
# - Check database connection
# - Check disk space
# - Review recent changes
# - Rollback if needed
```

### If Database is Down

```bash
# 1. Check status
docker exec skillpm_db pg_isready

# 2. Check logs
docker logs skillpm_db | tail -50

# 3. Restart database
docker restart skillpm_db

# 4. Verify data integrity
docker exec skillpm_db psql -U skillpm skillpm -c "SELECT COUNT(*) FROM skills;"

# 5. Rebuild from backup if corrupted
# See "Restore from Backup" section above
```

### If Disk is Full

```bash
# 1. Check space
df -h /

# 2. Find large files
du -sh /* | sort -h

# 3. Cleanup logs
docker logs skillpm --tail 100 > old_logs.txt
docker logs --tail 10 skillpm  # Keep only recent

# 4. Cleanup backups
# Keep only last 7 days
find /backups -name "*.gz" -mtime +7 -delete

# 5. Verify space freed
df -h /
```

---

## Team Communication

### Incident Report Template

```markdown
## Incident Report

**Date:** YYYY-MM-DD HH:MM:SS UTC
**Duration:** X minutes
**Impact:** Y users affected / Z requests failed

### What Happened
Brief description of the incident

### Root Cause
What caused it

### Immediate Actions
What was done to fix it

### Prevention
What we'll do to prevent it

### Timeline
- HH:MM - Detection
- HH:MM - Investigation
- HH:MM - Resolution
```

### Post-Incident Review

Scheduled within 24 hours of incident:

```markdown
## Post-Incident Review

**Attendees:** [names]
**Facilitator:** [name]

### What went well
-
-

### What could improve
-
-

### Action Items
- [ ] Task (Assigned to: Name)
```

---

## Useful Commands

```bash
# Overall status
docker-compose ps

# All logs (last 100 lines)
docker-compose logs --tail=100

# Restart everything
docker-compose restart

# Stop everything
docker-compose down

# Start everything
docker-compose up -d

# View specific service logs
docker logs skillpm -f

# Connect to database
psql -h db -U skillpm skillpm

# Backup database NOW
docker exec skillpm_db pg_dump -U skillpm skillpm | gzip > backup.sql.gz

# Check port usage
lsof -i :8000
```

---

## Contact & Escalation

### On-Call Schedule

- **Primary:** [Name] - [Number] - [Slack]
- **Secondary:** [Name] - [Number] - [Slack]

### Escalation Path

1. **Tier 1 (On-Call):** Investigate and fix
2. **Tier 2 (Lead):** If Tier 1 needs help after 15 min
3. **Tier 3 (Manager):** If issue unresolved after 1 hour

### Communication Channels

- **Incidents:** #skillpm-incidents (Slack)
- **Updates:** #skillpm-status (Slack)
- **General:** #skillpm-eng (Slack)

---

## Additional Resources

- [Deployment Guide](./DEPLOYMENT.md) - Full deployment instructions
- [Testing Guide](./TESTING.md) - How to run tests
- [Migrations Guide](./MIGRATIONS.md) - Database schema changes
- [Technical Review](./TECHNICAL_REVIEW.md) - Architecture overview

