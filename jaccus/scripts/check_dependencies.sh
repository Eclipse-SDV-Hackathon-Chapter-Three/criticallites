#!/bin/bash

# JACCUS Dependencies Check Script
# Ensures all required dependencies are available before running JACCUS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
CARLA_API_DIR="$HOME/carla-api"
PYTHON_API_DIR="$CARLA_API_DIR/PythonAPI"
AGENTS_DIR="$PYTHON_API_DIR/carla/agents"
REQUIREMENTS_FILE="$(dirname $0)/../targets/requirements.txt"

log_info "JACCUS Dependencies Checker"
log_info "=========================="

# Function to check if CARLA Python API is available
check_carla_python_api() {
    log_info "Checking CARLA Python API..."

    # Check if CARLA API directory exists
    if [[ ! -d "$CARLA_API_DIR" ]]; then
        log_error "CARLA API directory not found at $CARLA_API_DIR"
        return 1
    fi

    # Check if agents directory exists
    if [[ ! -d "$AGENTS_DIR" ]]; then
        log_error "CARLA agents directory not found at $AGENTS_DIR"
        log_info "This is required for BehaviorAgent functionality"
        return 1
    fi

    # Test if we can import CARLA and agents
    python3 -c "
import sys
sys.path.append('$PYTHON_API_DIR')
sys.path.append('$PYTHON_API_DIR/carla')
try:
    import carla
    from agents.navigation.behavior_agent import BehaviorAgent
    from agents.navigation.basic_agent import BasicAgent
    from agents.navigation.constant_velocity_agent import ConstantVelocityAgent
    print('CARLA and agents imported successfully')
except ImportError as e:
    print(f'Import error: {e}')
    exit(1)
" 2>/dev/null

    if [[ $? -eq 0 ]]; then
        log_success "CARLA Python API and agents are available"
        return 0
    else
        log_error "CARLA Python API or agents cannot be imported"
        return 1
    fi
}

# Function to install CARLA dependencies
install_carla_dependencies() {
    log_info "Installing CARLA dependencies..."

    # Check if we're in the right directory structure
    JACCUS_ROOT="$(dirname $0)/.."
    cd "$JACCUS_ROOT"

    if [[ -f "justfile" ]]; then
        # Use just to install client
        log_info "Using justfile to install CARLA client..."
        just install-client

        if [[ $? -eq 0 ]]; then
            log_success "CARLA client installed via justfile"
            return 0
        else
            log_error "Failed to install CARLA client via justfile"
            return 1
        fi
    else
        log_error "justfile not found. Cannot auto-install CARLA dependencies."
        log_info "Please run 'just install-client' from the jaccus directory"
        return 1
    fi
}

# Function to check Python dependencies
check_python_dependencies() {
    log_info "Checking Python dependencies..."

    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        # Check each requirement
        while IFS= read -r requirement || [[ -n "$requirement" ]]; do
            # Skip comments and empty lines
            if [[ "$requirement" =~ ^[[:space:]]*# ]] || [[ -z "$requirement" ]]; then
                continue
            fi

            # Extract package name (before ==, >=, etc.)
            package=$(echo "$requirement" | sed 's/[>=<].*//')

            # Handle packages with different import names
            import_name="$package"
            case "$package" in
                "eclipse-zenoh")
                    import_name="zenoh"
                    ;;
                "paho-mqtt")
                    import_name="paho.mqtt"
                    ;;
            esac

            python3 -c "import $import_name" 2>/dev/null
            if [[ $? -eq 0 ]]; then
                log_success "✓ $package"
            else
                log_warning "✗ $package (missing)"
                MISSING_DEPS+=("$requirement")
            fi
        done < "$REQUIREMENTS_FILE"

        if [[ ${#MISSING_DEPS[@]} -eq 0 ]]; then
            log_success "All Python dependencies are satisfied"
            return 0
        else
            log_warning "Missing dependencies: ${MISSING_DEPS[*]}"

            # Offer to install missing dependencies
            read -p "Install missing dependencies? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                pip3 install --user -r "$REQUIREMENTS_FILE"
                return $?
            fi
            return 1
        fi
    else
        log_warning "Requirements file not found at $REQUIREMENTS_FILE"
        return 1
    fi
}

# Function to check CARLA server connection
check_carla_server() {
    log_info "Checking CARLA server connection..."

    python3 -c "
import carla
import sys
try:
    client = carla.Client('localhost', 2000)
    client.set_timeout(2.0)
    world = client.get_world()
    print(f'Connected to CARLA server - Map: {world.get_map().name}')
except Exception as e:
    print(f'Cannot connect to CARLA server: {e}')
    sys.exit(1)
" 2>/dev/null

    if [[ $? -eq 0 ]]; then
        log_success "CARLA server is running and accessible"
        return 0
    else
        log_warning "CARLA server is not running or not accessible"
        log_info "Make sure CARLA server is running on localhost:2000"
        return 1
    fi
}

# Main dependency check function
main() {
    local carla_ok=0
    local python_ok=0
    local server_ok=0

    MISSING_DEPS=()

    # Check CARLA Python API
    if ! check_carla_python_api; then
        log_warning "Attempting to install CARLA dependencies..."
        if install_carla_dependencies; then
            # Re-check after installation
            if check_carla_python_api; then
                carla_ok=1
            fi
        fi
    else
        carla_ok=1
    fi

    # Check Python dependencies
    if check_python_dependencies; then
        python_ok=1
    fi

    # Check CARLA server (optional - warn but don't fail)
    if check_carla_server; then
        server_ok=1
    fi

    # Summary
    echo
    log_info "Dependency Check Summary:"
    echo "========================"

    if [[ $carla_ok -eq 1 ]]; then
        log_success "✓ CARLA Python API and agents"
    else
        log_error "✗ CARLA Python API and agents"
    fi

    if [[ $python_ok -eq 1 ]]; then
        log_success "✓ Python dependencies"
    else
        log_error "✗ Python dependencies"
    fi

    if [[ $server_ok -eq 1 ]]; then
        log_success "✓ CARLA server connection"
    else
        log_warning "⚠ CARLA server not running (start manually)"
    fi

    # Return success if critical dependencies are met
    if [[ $carla_ok -eq 1 && $python_ok -eq 1 ]]; then
        echo
        log_success "All critical dependencies satisfied! JACCUS is ready to run."
        return 0
    else
        echo
        log_error "Critical dependencies missing. Please resolve the issues above."
        return 1
    fi
}

# Run main function
main "$@"
