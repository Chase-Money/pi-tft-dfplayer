# AGENTS.md - Agent Guidelines for pi-tft-dfplayer

## Agent Workflow Requirements

**Before taking any actions:**
- Check `@docs/ai/TASK_LOG.md` for recent activities and maintain continuity between developers

**After any actions or changes:**
- Log all activities in `@docs/ai/TASK_LOG.md` to maintain continuity between developers

## Build/Lint/Test Commands
- **Install deps**: `pip install -r requirements.txt -r requirements-test.txt`
- **Run all tests**: `pytest`
- **Run single test**: `pytest tests/path/to/test_file.py::TestClass::test_method -v`
- **Run tests with coverage**: `pytest --cov=src --cov-report=html`
- **Lint**: `black src/ tests/ && flake8 src/ tests/ && mypy src/`
- **Format**: `black src/ tests/`

## Code Style Guidelines

### Python Standards
- **Python 3.9+**, 4-space indent, 88-char line length (Black)
- **Type hints** everywhere; use `from __future__ import annotations`
- **Constants** in `SCREAMING_SNAKE_CASE`
- **Small functions** with single responsibility; wrap hardware access in try/except
- **Dataclasses** for structured data; avoid mutable defaults

### Imports & Structure
- **Absolute imports** from project root (e.g., `from core.config import Config`)
- **Group imports**: stdlib, third-party, local (blank lines between)
- **No wildcard imports** (`from module import *`)
- **Explicit relative imports** within packages (`from ..framework import ScreenView`)

### Naming & Documentation
- **Classes**: `PascalCase` (e.g., `ApplicationState`, `TouchController`)
- **Functions/methods**: `snake_case` (e.g., `get_track_by_number`, `render_frame`)
- **Private**: `_underscore_prefix` (e.g., `_build_track_index`)
- **Docstrings**: Google-style with Args/Returns/Raises sections
- **Logging**: Use `logger = logging.getLogger(__name__)` extensively

### Error Handling & Hardware
- **Graceful degradation** on hardware failures; log and continue
- **Specific exceptions** over bare `except:`; catch expected errors
- **Resource cleanup** in `try/finally` or context managers
- **Thread safety** with `threading.Lock()` for shared state

### UI Framework
- **ScreenManagerV2** for navigation; inherit from `ScreenView`
- **UIEvent** for touch/press/drag/swipe events
- **Widgets** from `framework.widgets` (ButtonWidget, SliderWidget, etc.)
- **No hardcoded colors**; use theme system via `DFPLAYER_THEME`

### Testing
- **pytest** with fixtures; mock hardware dependencies
- **Descriptive test names**; test one behavior per test
- **Arrange-Act-Assert** pattern; use `pytest-mock` for mocking

### Git Workflow
- **Feature branches** only; keep `main` stable
- **Atomic commits** with clear messages
- **No destructive operations** without confirmation</content>
<parameter name="filePath">AGENTS.md