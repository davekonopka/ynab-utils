# ynab-utils

A collection of command line utilities for YNAB (You Need a Budget) users.

## Quick Start

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and run
git clone <repo-url>
cd ynab-utils
uv run ynab-utils --help
```

## Commands

### detect-dupes

Find potential duplicate transactions in your YNAB export.

```bash
# Basic usage - finds exact duplicates on same date
uv run ynab-utils detect-dupes --file transactions.csv

# Show all confidence levels (1=loosest, 5=strictest)
uv run ynab-utils detect-dupes --file transactions.csv --confidence 1

# Only check recent transactions
uv run ynab-utils detect-dupes --file transactions.csv --start-date 2025-01-01

# Adjust date matching window (default: 2 days)
uv run ynab-utils detect-dupes --file transactions.csv --days 5

# Output as JSON
uv run ynab-utils detect-dupes --file transactions.csv --output json
```

**Confidence levels:**
- 5: Same date, same amount, exact payee match
- 4: Same date, same amount, similar payee names
- 3: Within date window, same amount, exact/similar payee
- 2: Within date window, same amount, similar payee
- 1: Within date window, same amount only

## Development

```bash
# Install dev dependencies (includes pre-commit)
uv sync --extra dev

# Set up pre-commit hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=ynab_utils

# Lint code
uv run ruff check src/

# Format code
uv run ruff format src/

# Run pre-commit checks manually
uv run pre-commit run --all-files
```

**Git Commits:** This project uses [Conventional Commits](https://www.conventionalcommits.org/). Examples:
- `feat(detect-dupes): add --start-date filter`
- `fix(cli): correct argument parsing for --output`
- `test: add integration tests for date filtering`
