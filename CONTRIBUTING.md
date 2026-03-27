# Contributing to Digital Archive Maker

First off, thank you for considering contributing! 🎉

This project exists because of contributors like you, and we welcome contributions of all kinds.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

---

## How Can I Contribute?

### 🐛 Report Bugs
Found a bug? [Open an issue](../../issues/new) with:
- A clear, descriptive title
- Steps to reproduce the behavior
- Expected vs actual behavior
- Your environment (macOS version, Python version, etc.)

### 💡 Suggest Features
Have an idea? [Open an issue](../../issues/new) with:
- A clear description of the feature
- The problem it would solve
- Any implementation ideas you have

### 📖 Improve Documentation
Documentation improvements are always welcome:
- Fix typos or unclear explanations
- Add examples or use cases
- Translate to other languages

### 🔧 Submit Code
Ready to contribute code? See [Development Setup](#development-setup) below.

---

## Development Setup

### Project Structure

```
digital-archive-maker/
├── dam/                 # Shared library & unified CLI
│   ├── cli.py           # `dam` command entry point
│   ├── config.py        # Centralised configuration loader
│   ├── deps.py          # Dependency checker & installer
│   ├── keys.py          # Interactive API key onboarding
│   └── console.py       # Rich terminal output helpers
├── bin/
│   ├── music/           # CD ripping and tagging scripts
│   ├── video/           # Movie disc ripping scripts
│   ├── sync/            # Library sync scripts
│   ├── tv/              # TV show handling
│   └── utils/           # Helper tools
├── docs/                # Detailed guides
├── gui/                 # Desktop application
├── scripts/             # Utility scripts
├── tests/               # Test suite
├── assets/              # Project assets
├── cache/               # Temporary data
├── log/                 # Log files
├── config/              # Configuration templates
├── .github/             # GitHub workflows
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Python project configuration
├── Makefile             # Build and utility targets
└── .env.example         # Environment variables template
```

### Prerequisites

- macOS (primary development platform)
- Python 3.9+
- Homebrew

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/geniusworks/digital-archive-maker.git
cd digital-archive-maker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the project in editable mode (includes dam CLI + all deps)
pip install -e ".[dev]"
pip install -r requirements-test.txt

# Set up pre-commit hooks
pip install pre-commit
pre-commit install

# Copy environment template
cp .env.example .env

# Verify setup
dam check
make test
```

### Project Layout

| Directory | Purpose |
|-----------|--------|
| `dam/` | Shared library & unified CLI (`dam` command) |
| `bin/` | Individual pipeline scripts (music, video, sync, tv, utils) |
| `tests/` | pytest test suite |
| `docs/` | User-facing guides |

The `dam/` package provides centralised config loading (`dam.config`), dependency checking
(`dam.deps`), API key onboarding (`dam.keys`), and rich console output (`dam.console`).
New scripts should import from `dam.*` rather than re-implementing these patterns.

### Running Tests

The project has 81 tests covering core functionality. Install test dependencies first:
```bash
pip install -r requirements-test.txt
```

**Test options:**
```bash
# Run all tests (recommended)
make test

# Run with coverage report (HTML in htmlcov/index.html)
make test-coverage

# Run only fast unit tests
make test-unit

# Run only integration tests (may require external tools)
make test-integration

# Run specific test file
python -m pytest tests/test_fix_album.py -v

# Run specific test method
python -m pytest tests/test_fix_album.py::TestFixAlbum::test_url_encode -v

# Run tests matching a pattern
python -m pytest tests/ -k "test_url_encode" -v
```

**Test markers:**
- `unit` - Fast tests, no external dependencies
- `integration` - May require external tools (ffmpeg, abcde, etc.)
- `slow` - Network calls or large file operations

### Quick Test

For contributors: Run the test suite to verify everything works:
```bash
make test
```

This runs all tests with comprehensive coverage. See the commands above for more granular testing options.

---

## Pull Request Process

### Before You Start

1. **Check existing issues/PRs** to avoid duplicate work
2. **Open an issue first** for significant changes to discuss the approach
3. **Create a feature branch** from `main`

### Branch Naming

Use descriptive branch names:
- `feature/unified-cli` - New features
- `fix/genre-tagging-crash` - Bug fixes
- `docs/quickstart-guide` - Documentation
- `refactor/extract-api-clients` - Code refactoring

### Making Changes

1. **Write tests** for new functionality
2. **Update documentation** if needed
3. **Follow style guidelines** (see below)
4. **Keep commits focused** - one logical change per commit

### Submitting

1. **Push your branch** to your fork
2. **Open a Pull Request** against `main`
3. **Fill out the PR template** completely
4. **Request review** from maintainers

### PR Review Checklist

- [ ] Tests pass (`make test`)
- [ ] Code is formatted (`black .` and `isort .`)
- [ ] No linting errors (`flake8`)
- [ ] Documentation updated if needed
- [ ] Commit messages are clear

---

## Style Guidelines

### Python

We follow [PEP 8](https://pep8.org/) with these tools:

```bash
# Format code
black .

# Sort imports
isort .

# Check for issues
flake8
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files (new) | `snake_case.py` | `fix_album.py` |
| Functions | `snake_case` | `def fetch_metadata():` |
| Classes | `PascalCase` | `class AlbumTagger:` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES = 3` |

**Note:** Some existing files use `kebab-case` (e.g., `tag-explicit-mb.py`). New files should use `snake_case`, but don't rename existing files without discussion.

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): brief description

Longer explanation if needed.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
- `feat(music): add batch genre tagging`
- `fix(video): correct subtitle track numbering`
- `docs: add QUICKSTART guide`

---

## Reporting Bugs

### Security Vulnerabilities

**Do not open a public issue for security vulnerabilities.**

Instead, see [SECURITY.md](SECURITY.md) for responsible disclosure instructions.

### Regular Bugs

Please include:

1. **Summary**: What happened?
2. **Environment**: macOS version, Python version, script version
3. **Steps to reproduce**: Minimal steps to trigger the bug
4. **Expected behavior**: What should happen?
5. **Actual behavior**: What actually happened?
6. **Logs/output**: Relevant error messages or logs
7. **Workaround**: If you found one

---

## Suggesting Features

We love feature suggestions! Please include:

1. **Problem**: What problem does this solve?
2. **Solution**: How would this feature work?
3. **Alternatives**: What other solutions did you consider?
4. **Context**: Any additional context or screenshots

---

## 🎨 Style Guide

### **Emoji Language Standard**
For consistency across the project, please follow our emoji standards:

#### **Status Indicators:**
```
✅ Success/Complete/OK
❌ Error/Failure/Missing
⚠️ Warning/Optional/Caution
```

#### **Feature Categories:**
```
🎵 Music/Audio Content
📀 Physical Media (CD/DVD/Blu-ray)
🏷️ Tagging/Metadata
📺 Video/TV Content
🎬 Movies/Film
⚙️ Settings/Configuration
```

#### **Actions & Processes:**
```
🚀 Start/Run/Execute
🔧 Fix/Configure/Tools
💡 Tips/Information
🔍 Check/Search/Inspect
```

**Emoji Standards**: Use consistent status indicators (✅❌⚠️), feature categories (🎵📀🏷️), and actions (🚀🔧💡) throughout the project.

---

## Recognition

Contributors will be recognized in:
- The project README
- Release notes for significant contributions
- The AUTHORS file (if created)

---

## Questions?

- Open a [Discussion](../../discussions) for questions
- Check existing issues for answers
- Read the documentation in `docs/`

Thank you for contributing! 🙏
