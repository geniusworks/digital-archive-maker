# Contributing to Digital Library

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

### Prerequisites

- macOS (primary development platform)
- Python 3.9+
- Homebrew

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/geniusworks/digital-library.git
cd digital-library

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Install development tools
pip install black isort flake8 mypy

# Copy environment template
cp .env.sample .env

# Run tests to verify setup
make test
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
python -m pytest tests/test_fix_album.py -v
```

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
