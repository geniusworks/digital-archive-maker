#!/bin/bash

# Local Pipeline Test Script
# Mirrors .github/workflows/ci.yml for local testing before push

set -e  # Exit on any error

echo "🚀 Running local pipeline test..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Test 1: Python versions (we'll test with current Python)
echo "📋 Testing Python setup..."
python_version=$(python3 --version 2>&1)
print_status "Python: $python_version"

# Test 2: Install dependencies
echo ""
echo "📦 Setting up virtual environment..."
if [ -f "requirements.txt" ]; then
    # Create/activate virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Configure for PEP 668 compatibility
    echo "[global]" > venv/pip.conf
    echo "break-system-packages = true" >> venv/pip.conf
    
    # Activate and install
    source venv/bin/activate
    # Use full path to python to avoid PATH issues
    VENV_PYTHON="$(pwd)/venv/bin/python"
    $VENV_PYTHON -m pip install --upgrade pip --quiet
    $VENV_PYTHON -m pip install -r requirements.txt --quiet
    print_status "Dependencies installed"
else
    print_error "requirements.txt not found"
    exit 1
fi

if [ -f "requirements-test.txt" ]; then
    $VENV_PYTHON -m pip install -r requirements-test.txt --quiet
    print_status "Test dependencies installed"
fi

# Test 3: Code formatting (black)
echo ""
echo "🎨 Checking code formatting with black..."
if $VENV_PYTHON -c "import black" 2>/dev/null; then
    if $VENV_PYTHON -m black --check --diff bin/ tests/; then
        print_status "Code formatting OK"
    else
        print_warning "Code formatting issues found (run '$VENV_PYTHON -m black bin/ tests/' to fix)"
    fi
else
    print_warning "black not installed, skipping formatting check"
fi

# Test 4: Import sorting (isort)
echo ""
echo "📚 Checking import sorting with isort..."
if $VENV_PYTHON -c "import isort" 2>/dev/null; then
    if $VENV_PYTHON -m isort --check-only --diff bin/ tests/; then
        print_status "Import sorting OK"
    else
        print_warning "Import sorting issues found (run '$VENV_PYTHON -m isort bin/ tests/' to fix)"
    fi
else
    print_warning "isort not installed, skipping import sorting check"
fi

# Test 5: Linting (flake8)
echo ""
echo "🔍 Linting with flake8..."
if $VENV_PYTHON -c "import flake8" 2>/dev/null; then
    echo "Critical errors (E9,F63,F7,F82):"
    if $VENV_PYTHON -m flake8 bin/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
        print_status "No critical linting errors"
    else
        print_error "Critical linting errors found"
    fi
    
    echo "Style warnings (max line length, complexity):"
    $VENV_PYTHON -m flake8 bin/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics
    print_status "Linting check completed"
else
    print_warning "flake8 not installed, skipping linting"
fi

# Test 6: Run tests
echo ""
echo "🧪 Running tests..."
if [ -d "tests" ] && [ "$(ls -A tests)" ]; then
    if $VENV_PYTHON -c "import pytest" 2>/dev/null; then
        if $VENV_PYTHON -m pytest tests/ -v --tb=short; then
            print_status "All tests passed"
        else
            print_error "Some tests failed"
            exit 1
        fi
    else
        print_warning "pytest not installed, skipping tests"
    fi
else
    print_warning "No tests directory or empty, skipping tests"
fi

# Test 7: Check if core scripts can import
echo ""
echo "🔧 Checking script imports..."
scripts_to_test=("dam/cli.py" "dam/config.py" "dam/deps.py")
for script in "${scripts_to_test[@]}"; do
    if [ -f "$script" ]; then
        if $VENV_PYTHON -c "import sys; sys.path.insert(0, '.'); import importlib.util; spec = importlib.util.spec_from_file_location('test', '$script'); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)" 2>/dev/null; then
            print_status "$script imports OK"
        else
            print_error "$script failed to import"
        fi
    fi
done

echo ""
echo "=================================="
print_status "Local pipeline test completed!"
echo ""
echo "💡 Tips:"
echo "   - Fix formatting: $VENV_PYTHON -m black bin/ tests/"
echo "   - Fix imports: $VENV_PYTHON -m isort bin/ tests/"
echo "   - Run specific tests: $VENV_PYTHON -m pytest tests/test_file.py"
echo "   - Check specific file: $VENV_PYTHON -m flake8 bin/script.py"
