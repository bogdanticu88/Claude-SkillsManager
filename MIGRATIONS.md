# Database Migrations Guide

## Overview

This guide explains how to manage database schema changes safely using Alembic.

## Why Migrations Matter

Without migrations:
- Can't safely evolve schema in production
- Manual SQL changes cause inconsistencies
- No rollback capability for failed deployments
- Team members have different schema versions

With Alembic:
- Schema changes are version controlled
- Can rollback to previous schema
- Automatic upgrade/downgrade
- Team stays in sync

## Setup (First Time Only)

### 1. Install Alembic
```bash
pip install alembic>=1.13.0
```

### 2. Initialize Migration Environment
```bash
cd registry
alembic init alembic
cd ..
```

This creates:
```
registry/
  alembic/
    env.py                 # Alembic configuration
    script.py.mako         # Migration template
    versions/              # Migration files go here
    alembic.ini            # Alembic settings
```

### 3. Configure Alembic
Edit `registry/alembic/env.py` to use your SQLAlchemy models:

```python
from registry.db.models import Base
from registry.db.connection import DATABASE_URL

# In env.py:
target_metadata = Base.metadata
sqlalchemy_url = DATABASE_URL
```

Edit `registry/alembic.ini`:
```ini
# Set database URL
sqlalchemy.url = sqlite:///skillpm.db

# Or use environment variable
sqlalchemy.url = driver://user:pass@localhost/dbname
```

## Creating Migrations

### Auto-Generate Migration
When you change a model, auto-generate the migration:

```bash
cd registry
alembic revision --autogenerate -m "add user bio field"
cd ..
```

This creates `registry/alembic/versions/001_add_user_bio.py` with:
```python
def upgrade():
    op.add_column('users', sa.Column('bio', sa.Text()))

def downgrade():
    op.drop_column('users', 'bio')
```

### Manual Migration
For complex changes:

```bash
cd registry
alembic revision -m "custom migration"
cd ..
```

Then edit the created file with custom SQL.

## Running Migrations

### Upgrade to Latest
```bash
cd registry
alembic upgrade head
cd ..
```

### Downgrade One Step
```bash
cd registry
alembic downgrade -1
cd ..
```

### Downgrade to Specific Version
```bash
cd registry
alembic downgrade 001_add_user_bio
cd ..
```

### Check Current Version
```bash
cd registry
alembic current
cd ..
```

### View All Versions
```bash
cd registry
alembic history
cd ..
```

## Migration Best Practices

### ✅ DO

1. **Make migrations small and focused**
   ```python
   # Good: One change per migration
   def upgrade():
       op.add_column('users', sa.Column('bio', sa.Text()))
   ```

2. **Always write downgrade()**
   ```python
   def upgrade():
       op.add_column('users', sa.Column('bio', sa.Text()))

   def downgrade():
       op.drop_column('users', 'bio')
   ```

3. **Test migrations locally first**
   ```bash
   # Test upgrade
   alembic upgrade head

   # Test downgrade
   alembic downgrade -1

   # Test upgrade again
   alembic upgrade head
   ```

4. **Use meaningful names**
   ```python
   # Good
   def upgrade():
       """Add user bio field to store biography"""

   # Bad
   def upgrade():
       """migrations"""
   ```

5. **Review generated migrations**
   Auto-generated migrations sometimes need tweaks

### ❌ DON'T

1. **Don't lose data**
   ```python
   # Bad: Drops data
   op.drop_column('users', 'email')

   # Good: Keep data
   op.add_column('users', sa.Column('email_old', sa.String))
   op.drop_column('users', 'email')
   ```

2. **Don't commit without downgrade**
   ```python
   # Bad
   def downgrade():
       raise NotImplementedError()

   # Good
   def downgrade():
       op.drop_column('users', 'bio')
   ```

3. **Don't run in production without testing**
   - Test in staging first
   - Backup database before running
   - Have rollback plan ready

4. **Don't edit migrations after they're deployed**
   - Create a new migration instead

## Example: Adding a Field

### Step 1: Update Model
```python
# registry/db/models.py
class User(Base):
    # ... existing fields ...
    bio = Column(Text, nullable=True)  # NEW FIELD
```

### Step 2: Generate Migration
```bash
cd registry
alembic revision --autogenerate -m "add user bio"
cd ..
```

Creates `registry/alembic/versions/001_add_user_bio.py`:
```python
def upgrade():
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('users', 'bio')
```

### Step 3: Test Locally
```bash
# Upgrade
alembic upgrade head
# Check database
sqlite3 skillpm.db "SELECT sql FROM sqlite_master WHERE type='table' AND name='users';"
# Should show bio column

# Downgrade
alembic downgrade -1
# Check database again
sqlite3 skillpm.db "SELECT sql FROM sqlite_master WHERE type='table' AND name='users';"
# bio column should be gone

# Upgrade again
alembic upgrade head
```

### Step 4: Deploy
```bash
# In staging
alembic upgrade head

# In production (after testing)
alembic upgrade head
```

## Example: Renaming a Column

```python
# registry/alembic/versions/002_rename_author_name.py

def upgrade():
    # Step 1: Add new column
    op.add_column('skills', sa.Column('author_new', sa.String(256)))

    # Step 2: Copy data
    op.execute("UPDATE skills SET author_new = author")

    # Step 3: Drop old column
    op.drop_constraint('fk_author', 'skills')  # Drop FK if exists
    op.drop_column('skills', 'author')

    # Step 4: Rename
    op.alter_column('skills', 'author_new', new_column_name='author')

def downgrade():
    # Reverse all steps
    op.add_column('skills', sa.Column('author_old', sa.String(256)))
    op.execute("UPDATE skills SET author_old = author")
    op.drop_column('skills', 'author')
    op.alter_column('skills', 'author_old', new_column_name='author')
```

## Version Control

Migrations are part of your code:

```bash
# Check in migrations
git add registry/alembic/versions/
git commit -m "Add user bio field migration"

# Check in alembic.ini
git add registry/alembic.ini
git add registry/alembic/env.py
```

## Deployment Checklist

Before deploying a migration:

- [ ] Migration is reviewed and tested
- [ ] Downgrade path works
- [ ] Backup of database exists
- [ ] Tested in staging environment
- [ ] Team knows about the change
- [ ] Plan for rollback if needed
- [ ] Monitor after deployment

## Troubleshooting

### Migration Fails to Apply

1. Check migration syntax
   ```bash
   alembic heads  # Show pending migrations
   ```

2. Check database logs
   ```bash
   # If using PostgreSQL
   tail -f /var/log/postgresql/postgresql.log
   ```

3. Downgrade to last known good
   ```bash
   alembic downgrade -1
   ```

### Migration Out of Sync

```bash
# Stamp current database state
alembic stamp head

# Then generate new migration for actual changes
alembic revision --autogenerate -m "fix schema sync"
```

### Lost Migration

Don't edit migrations after deployment. Create a new one:

```python
# registry/alembic/versions/003_fix_previous_migration.py

def upgrade():
    # Fix what was wrong
    op.alter_column('users', 'bio', new_column_name='biography')

def downgrade():
    op.alter_column('users', 'biography', new_column_name='bio')
```

## Next Steps

1. Initialize Alembic (follow Setup section)
2. Create initial migration
   ```bash
   alembic revision --autogenerate -m "initial schema"
   ```
3. Test it works
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```
4. Check in to version control
5. Deploy to staging
6. Deploy to production

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Database Migrations Best Practices](https://www.liquibase.org/get-started/best-practices)

