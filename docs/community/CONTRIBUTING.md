# SkillPM Contribution Guidelines

Thank you for your interest in contributing to SkillPM! We are building the decentralized future of AI skills, and your help is vital.

## How to Contribute

### 1. Creating Skills
The most valuable way to contribute is by building and publishing high-quality skills.
* Follow the [Manifest Specification](../../pkg/manifest/skill.schema.json).
* Ensure your skill is well-documented with a `README.md`.
* Include tests for your skill logic.
* Sign your manifest using `skillpm package` before publishing.

### 2. Improving the Platform
* **CLI (Go)**: Help us improve the execution engine, sandboxing, or CLI usability.
* **Registry (FastAPI)**: Improve the backend API, search algorithms, or authorization model.
* **Web (Next.js)**: Enhance the registry UI, creator dashboard, or discovery features.

### 3. Reporting Issues
Use GitHub issues to report bugs or request features. Please include:
* A clear description of the issue.
* Steps to reproduce (if a bug).
* Your environment details (OS, Go version, SkillPM version).

## Review Process
* All platform contributions require a Pull Request.
* PRs will be reviewed by at least one maintainer.
* Skills published to the registry may undergo automated and manual security reviews.

## Security First
If you discover a security vulnerability, please do NOT open a public issue. Instead, email security@skillpm.dev.
