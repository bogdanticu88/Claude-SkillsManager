# Contributing to SkillPM

SkillPM is open source and accepts contributions. This guide explains how to set up your development environment, run tests, and submit pull requests.

---

## Code of conduct

We expect contributors to be respectful and professional in all interactions. If you encounter behavior that violates this, report it to the maintainers.

---

## Development setup

### Backend

Requirements: Python 3.12+, PostgreSQL 12+, Redis 6+.

Clone the repository:

```bash
git clone https://github.com/yourusername/skillpm.git
cd skillpm/registry
```

Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set up your environment:

```bash
cp ../.env.example ../.env
```

Edit `.env` and set the database and Redis connection strings to point to your local instances.

Start the API in development mode:

```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000. Swagger docs are at http://localhost:8000/docs.

### CLI

Requirements: Go 1.21+.

Build the CLI:

```bash
cd skillpm
go build -o skillpm
./skillpm --help
```

---

## Making changes

Before you start working on a change, open an issue to discuss it with the maintainers. This avoids duplication and ensures the change aligns with the project roadmap.

When you are ready to submit code:

1. Create a feature branch:

```bash
git checkout -b feature/your-feature-name
```

2. Make your changes. Keep commits focused and write clear commit messages.

3. Add or update tests to cover your changes.

4. Run the test suite to ensure nothing broke:

```bash
cd registry
python -m pytest ../tests/ -v
```

5. Check code formatting. The project uses black and isort:

```bash
pip install black isort
black registry/
isort registry/
```

6. Push your branch and open a pull request.

---

## Testing

All changes must include tests. The test suite uses pytest.

Run all tests:

```bash
cd registry
python -m pytest ../tests/ -v
```

Run with coverage:

```bash
python -m pytest ../tests/ --cov=. --cov-report=html
```

Create a new test file for new features. Follow the naming convention `test_<feature>.py`.

Keep test names descriptive and use docstrings to explain what is being tested:

```python
def test_skill_creation_requires_authentication():
    """Unauthenticated requests to create a skill should return 401."""
    response = client.post("/api/v1/skills/", json={...})
    assert response.status_code == 401
```

---

## Code style

- Use snake_case for variables and functions
- Use PascalCase for classes
- Add type hints to function signatures
- Keep functions and classes small and focused
- Write docstrings for public functions and classes
- Use blank lines to separate logical sections

Example:

```python
def validate_skill_name(name: str) -> bool:
    """Check if a skill name is valid.
    
    A valid name contains only lowercase letters, numbers, and hyphens.
    Names must be between 3 and 64 characters.
    """
    if not name or len(name) < 3 or len(name) > 64:
        return False
    return all(c.isalnum() or c == '-' for c in name)
```

---

## Commit messages

Write clear, descriptive commit messages:

- Use imperative mood: "Add feature" not "Added feature"
- Keep the first line to 50 characters or less
- Wrap the body at 72 characters
- Explain what and why, not how

Example:

```
Add per-user rate limiting to API

Rate limiting is now 100 requests per hour per authenticated user.
Unauthenticated requests are not rate limited. This prevents abuse
of the registry by a single user account.
```

---

## Pull requests

When you open a pull request:

- Reference any related issues in the description
- Describe what your change does and why
- Keep the scope focused. Large changes should be split into multiple PRs
- Ensure all tests pass
- Run the linter and formatter

Example PR description:

```
Closes #123

This PR adds validation for skill names on the API side. Previously
only the CLI validated names. Now the API enforces that names are
lowercase alphanumeric with hyphens, between 3 and 64 characters.

Includes:
- New validation function in schemas/skill.py
- Tests in test_skill_validation.py
- Error message improvements for invalid names
```

---

## Release process

Releases are tagged with semantic versioning (v1.0.0, v1.1.0, etc). Maintainers handle release tagging and publishing.

---

## Questions

If you have questions, open an issue or start a discussion. Do not email maintainers directly.

---

Thank you for contributing to SkillPM.
