# Contributing to IdeaHunter

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-org/IdeaHunter.git
   cd IdeaHunter
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies (including dev tools):**

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   # Or, using pyproject.toml:
   pip install -e ".[dev]"
   ```

4. **Copy the environment file and configure:**

   ```bash
   cp .env.example .env
   # Edit .env with your LLM_API_KEY, LLM_BASE_URL, etc.
   ```

## Adding a New Scraper Plugin

IdeaHunter uses a plugin architecture for data sources. To add a new scraper:

1. **Create a new file** in `plugins/`, e.g. `plugins/reddit_scraper.py`.

2. **Inherit from `BaseScraper`:**

   ```python
   from plugins.base_scraper import BaseScraper, RawItem

   class RedditScraper(BaseScraper):
       source_name = "reddit"

       def fetch_raw_items(self, max_items: int | None = None) -> list[RawItem]:
           # Implement fetching logic here
           ...

       def close(self) -> None:
           # Clean up any resources (HTTP clients, etc.)
           ...
   ```

3. **Register the scraper** in `plugins/registry.py`:

   ```python
   from plugins.reddit_scraper import RedditScraper
   register_scraper("reddit", RedditScraper)
   ```

4. **Update `core/orchestrator.py`** if needed (add to `get_scraper()` mapping).

5. **Add tests** in `tests/` covering the new scraper.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=plugins --cov=api --cov-report=term-missing

# Run a specific test file
pytest tests/test_orchestrator.py -v
```

## Linting

```bash
# Check style
ruff check .

# Auto-fix issues
ruff check --fix .
```

## Pull Request Guidelines

1. **Branch from `main`** and give your branch a descriptive name (e.g. `feat/reddit-scraper`, `fix/dedup-logic`).

2. **Keep PRs focused.** One feature or fix per PR.

3. **Write tests** for new functionality. Aim for reasonable coverage of the happy path and key edge cases.

4. **Run linting and tests** before submitting:

   ```bash
   ruff check .
   pytest
   ```

5. **Write a clear PR description** explaining what changes were made and why.

6. **Be responsive to review feedback.** We aim to review PRs within a few days.

## Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting (rules: E, F, I, UP, B).
- Line length limit: 100 characters.
- Target Python version: 3.10+.
- Type hints are encouraged for all public functions.

## Questions?

Open an issue or start a discussion. We are happy to help!
