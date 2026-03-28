# SkillPM Testing Guide

## Running Tests

### Prerequisites
```bash
cd registry
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_validation.py -v
```

### Run Specific Test
```bash
pytest tests/test_validation.py::TestSkillValidation::test_valid_skill -v
```

### Run Tests by Mark
```bash
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m validation    # Only validation tests
```

### Run with Coverage
```bash
pip install pytest-cov
pytest tests/ --cov=registry --cov-report=html
```

## Test Organization

### Validation Tests (`test_validation.py`)
Tests that input validation works correctly:
- Skill name validation (lowercase, no underscores, reserved names)
- Skill version validation (semver format)
- Skill language validation
- User username validation
- Email validation
- URL validation
- Field length limits

**Target:** 100% validation coverage

### Error Handling Tests (`test_api_errors.py`)
Tests that errors follow standard format:
- Validation errors return proper response
- Authentication errors are clear
- Not found errors are clear
- Rate limiting errors include retry info
- Request ID tracking for debugging
- Request size limits enforced
- CORS headers present

**Target:** All error paths return standard format

### Current Test Count
- Validation tests: 20+ test cases
- Error handling tests: 10+ test cases
- **Total: 30+ tests**

## Test Coverage Goals

| Component | Target | Notes |
|-----------|--------|-------|
| Input validation | 100% | Every field validated |
| Error handling | 100% | Every error path tested |
| Authentication | 90%+ | API key verification |
| Rate limiting | 80%+ | Per-user limits |
| Database models | 80%+ | CRUD operations |
| API endpoints | 70%+ | Happy path + errors |
| **Overall** | **70%+** | Focus on critical paths |

## Writing New Tests

### Example: Testing a Validation
```python
def test_skill_name_too_short(self):
    """Skill names must be at least 3 characters"""
    with pytest.raises(ValidationError):
        SkillCreate(
            name="ab",  # Too short
            version="1.0.0",
            description="A valid skill description",
            language="python",
            entry_point="skill.py",
            repository_url="https://github.com/test/test",
            author_username="testuser"
        )
```

### Example: Testing an API Endpoint
```python
def test_create_skill_success(self):
    """POST /skills should create skill"""
    api_key = "skpm_test_key"  # Use test key

    response = client.post(
        "/api/v1/skills/",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "name": "test-skill",
            "version": "1.0.0",
            "description": "A valid skill description",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/test",
            "author_username": "testuser"
        }
    )
    assert response.status_code == 201
    assert response.json()["name"] == "test-skill"
```

## Continuous Integration

Tests should run on:
- Every commit (pre-commit hook)
- Every PR (CI/CD)
- Before release

### Example: GitHub Actions (.github/workflows/test.yml)
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -r registry/requirements.txt pytest pytest-cov
      - run: pytest tests/ --cov=registry --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Known Issues & Future Tests

These need tests but don't exist yet:
- [ ] Database migration tests
- [ ] Concurrent request handling
- [ ] Large dataset performance
- [ ] Sandbox security (seccomp filtering)
- [ ] GPG signing/verification
- [ ] Workflow execution
- [ ] Breaking change detection
- [ ] Version resolution
- [ ] Cache invalidation

## Debugging Failed Tests

### Enable verbose output
```bash
pytest -vv tests/test_validation.py
```

### Show print statements
```bash
pytest -s tests/test_validation.py
```

### Drop into debugger on failure
```bash
pytest --pdb tests/test_validation.py
```

### Run with logging
```bash
pytest --log-cli-level=DEBUG tests/test_validation.py
```

## Performance Testing

Coming in Stage 2:
- Load testing (concurrent users)
- Response time benchmarks
- Database query optimization
- Cache hit rates

## Security Testing

Coming in Stage 2:
- SQL injection attempts
- XSS in user inputs
- CSRF protection
- Rate limit bypass attempts
- Sandbox escape tests

## Test Metrics

Track these over time:
- Test count
- Code coverage %
- Failed tests per commit
- Test execution time
- New bugs found in beta vs production

