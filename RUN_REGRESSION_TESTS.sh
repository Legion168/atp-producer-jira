#!/bin/bash
# Regression Test Script for ATP Producer Jira
# Run this after making changes to ensure no regressions

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                   ATP PRODUCER REGRESSION TEST SUITE                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "tests/test_use_case_coverage.py" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

echo "📋 Pre-flight Checks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python version
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓${NC} Python: $PYTHON_VERSION"

# Check for required packages
echo ""
echo "📦 Checking Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MISSING_DEPS=()

for pkg in pytz python-dateutil requests; do
    if python3 -c "import ${pkg//-/_}" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $pkg installed"
    else
        echo -e "${RED}✗${NC} $pkg missing"
        MISSING_DEPS+=("$pkg")
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠ Missing dependencies detected${NC}"
    echo "Run: pip install ${MISSING_DEPS[@]}"
    echo "Or: pip install -r requirements.txt"
    exit 1
fi

# Syntax check
echo ""
echo "🔍 Syntax Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

FILES=(
    "app/cycle_time_calculator.py"
    "app/cycle_time_strategy.py"
    "app/simple_cycle_time_strategy.py"
    "app/complex_cycle_time_strategy.py"
    "tests/test_use_case_coverage.py"
    "tests/test_helpers.py"
)

for file in "${FILES[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file has syntax errors"
        exit 1
    fi
done

# Run tests
echo ""
echo "🧪 Running Test Suite"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run with the coverage report
if python3 tests/test_use_case_coverage.py; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${RED}❌ TESTS FAILED${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi

