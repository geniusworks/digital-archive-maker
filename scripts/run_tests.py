#!/usr/bin/env python3
"""
Test runner for digital library scripts.
"""

import sys
import subprocess


def run_command(cmd, description):
    """Run a command and handle the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)
    print()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Run all tests."""
    print()

    # Check test dependencies are installed
    print("Checking test dependencies...")
    print()

    try:
        import pytest  # noqa
        import pytest_cov  # noqa
        import pytest_mock  # noqa
        import requests_mock  # noqa

        print("✅ All test dependencies are available")
    except ImportError as e:
        print(f"❌ Missing test dependency: {e}")
        print("Install with: pip install -r requirements-test.txt")
        sys.exit(1)

    # Run different test suites
    success = True

    # Unit tests (fast)
    success &= run_command(
        [sys.executable, "-m", "pytest", "tests/", "-m", "unit", "-v"], "Unit tests"
    )

    # Integration tests (may require external tools)
    success &= run_command(
        [sys.executable, "-m", "pytest", "tests/", "-m", "integration", "-v"], "Integration tests"
    )

    # All tests with coverage
    success &= run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=bin",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-fail-under=25",
        ],
        "All tests with coverage",
    )

    if success:
        print("\n✅ All tests passed!")
        print("\nCoverage report generated in htmlcov/index.html")
        print()
    else:
        print("\n❌ Some tests failed!")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
