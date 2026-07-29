# Contributing to fastapi-sliding-window

First off, thanks for taking the time to contribute! 🎉

This project is a rate-limiting library for FastAPI. We welcome all kinds of contributions — bug reports, feature suggestions, documentation improvements, and code changes.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Reporting Issues](#reporting-issues)
- [AI/LLM-Assisted Contributions](#aillm-assisted-contributions)
- [License](#license)

---

## Code of Conduct

This project adheres to the [Contributor Covenant](https://www.contributor-covenant.org/). By participating, you are expected to uphold this code. Please report unacceptable behavior to the maintainers.

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork:

   ```bash
   git clone git@github.com:YOUR_USERNAME/fastapi-sliding-window.git
   cd fastapi-sliding-window
   ```

3. **Set up a virtual environment** (Python 3.10+):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

4. **Install the project in editable mode with dev and redis extras**:

   ```bash
   pip install -e ".[dev,redis]"
   ```

5. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

   Pre-commit will automatically run ruff (lint + format), mypy, and pytest on every commit.

---

## Development Workflow

### Code style

We use [Ruff](https://github.com/astral-sh/ruff) (lint + format) and [mypy](https://mypy-lang.org/) (strict mode).

Run all checks before pushing:

```bash
ruff check fastapi_sliding_window/
ruff format --check fastapi_sliding_window/
mypy fastapi_sliding_window/
```

To auto-fix lint issues and format:

```bash
ruff check --fix fastapi_sliding_window/
ruff format fastapi_sliding_window/
```

### Testing

Tests use pytest with pytest-asyncio:

```bash
pytest tests/ -v
```

Run a specific test file:

```bash
pytest tests/test_algorithms.py -v
```

Run a single test:

```bash
pytest tests/test_algorithms.py -v -k "test_gcra"
```

When adding new functionality, please include tests that cover it. We aim for good coverage, especially for edge cases (e.g., `limit=0`, `cost>1`, concurrent access).

### Pre-commit hooks

The `.pre-commit-config.yaml` runs four checks on every commit:

| Hook | What it does |
|------|-------------|
| `ruff` | Lints and auto-fixes issues |
| `ruff-format` | Formats code consistently |
| `mypy` | Static type checking (strict mode) |
| `pytest` | Runs the full test suite |

You can run them manually at any time:

```bash
pre-commit run --all-files
```

---

## Pull Request Guidelines

### Branching

- `develop` is the main development branch. Open all PRs against `develop`.
- Use feature branches: `feat/my-new-feature`, `fix/issue-123`, `docs/readme-update`.
- `main` is reserved for releases and is updated only via the CI release workflow.

### Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add WebSocket rate limiting support
fix: correct retry-after header calculation
docs: add examples for GCRA algorithm
test: add thread-safety tests for TokenBucket
refactor: simplify Limiter._check_items logic
ci: pin pyaction-pypi-publish to v1.14.1
chore: bump version to 0.3.0
```

This keeps history clean and helps automate changelog generation.

### PR Checklist

Before submitting your PR, verify:

- [ ] Code passes `ruff check --fix` and `ruff format --check`
- [ ] `mypy fastapi_sliding_window/` reports no errors
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] New functionality includes corresponding tests
- [ ] Public API changes are reflected in `README_en.md` (or `README.md` for Russian)
- [ ] Changes are backward compatible, or a discussion issue was opened first

### PR Description

Please include:

- **What** this PR changes and **why**.
- **Issue number** if it fixes or relates to an issue (e.g., `Closes #123`).
- **Screenshots** or logs if the change is user-visible (e.g., new HTTP headers).
- **Breaking changes** must be clearly documented.

---

## Reporting Issues

### Bug reports

When filing a bug, please include:

- **Environment**: Python version, OS, library version (`pip show fastapi-sliding-window`).
- **Minimal reproduction**: A short code snippet that demonstrates the issue.
- **Expected vs actual** behavior.
- **Logs or error messages** if any.

### Feature requests

We'd love to hear your ideas! Please include:

- **Problem** you're trying to solve.
- **Proposed solution** (feel free to sketch an API).
- **Alternatives** you've considered.

---

## AI/LLM-Assisted Contributions

We welcome contributions made with the help of AI/LLM tools. However, by submitting a PR you certify that:

1. **You understand the code** you're submitting and can explain it if asked.
2. **You take responsibility** for its correctness, testing, and adherence to project standards.
3. **You have reviewed the output** and are not submitting AI-generated code blindly.

**Purely automated or unattended AI-generated PRs — where a human has not meaningfully reviewed, tested, or understood the changes — will be closed.** Such PRs consume maintainer time that could be spent on engaged contributors.

If an AI tool helped produce your changes, consider adding a `Co-authored-by` trailer to your commit message to credit it. This is not required but helps set expectations during review.

---

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers the project.
