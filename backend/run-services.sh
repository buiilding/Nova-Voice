#!/bin/bash
# ===========================================
# NOVA VOICE - Run All Backend Services
# ===========================================
# This script runs all three backend services:
# - Gateway (WebSocket server)
# - STT Worker (Speech-to-text)
# - Translation Worker (Language translation)
#
# Usage: ./run-services.sh [dev|prod]
#   dev: Run with python -m (development mode)
#   prod: Run with docker-compose (Docker mode)
#   (default: dev)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Copying from .env_example..."
        if [ -f ".env_example" ]; then
            cp .env_example .env
            print_success "Created .env file from .env_example"
            print_info "Edit .env file to customize settings if needed"
        else
            print_error ".env_example not found. Please create .env manually."
            exit 1
        fi
    fi
}

# Function to run services in development mode
run_dev() {
    print_info "Starting services in DEVELOPMENT mode..."
    print_info "This will run all services with python -m commands"

    # Check if conda environment exists
    CONDA_ENV_NAME="nova-voice"
    if command -v conda &> /dev/null; then
        if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
            print_info "Activating conda environment: ${CONDA_ENV_NAME}"
            # Source conda activation script
            CONDA_BASE=$(conda info --base)
            source "${CONDA_BASE}/etc/profile.d/conda.sh"
            conda activate "${CONDA_ENV_NAME}"
        else
            print_warning "Conda environment '${CONDA_ENV_NAME}' not found."
            print_info "Create it with: conda env create -f environment.yml"
            print_info "Or manually: conda create -n ${CONDA_ENV_NAME} python=3.10"
            print_info "Then activate: conda activate ${CONDA_ENV_NAME}"
            print_info "Using system Python for now..."
        fi
    else
        print_warning "Conda not found. Looking for virtual environment..."

        # Fallback to virtual environment
        if [ -d "venv" ]; then
            print_info "Activating virtual environment..."
            source venv/bin/activate
        elif [ -d ".venv" ]; then
            print_info "Activating virtual environment..."
            source .venv/bin/activate
        else
            print_warning "No conda or virtual environment found. Using system Python."
            print_info "Consider creating a conda environment:"
            print_info "  conda create -n nova-voice python=3.10"
            print_info "  conda activate nova-voice"
        fi
    fi

    # Install/update requirements
    print_info "Installing/updating requirements..."
    pip install -r requirements.txt

    # Function to start a service in background
    start_service() {
        local service_name=$1
        local service_path=$2
        local log_file="${service_name}.log"

        print_info "Starting ${service_name}..."
        python -m ${service_path} > "${log_file}" 2>&1 &
        local pid=$!
        echo $pid > "${service_name}.pid"
        print_success "${service_name} started (PID: ${pid}) - logs: ${log_file}"
    }

    # Start Redis if not running
    if ! pgrep -x "redis-server" > /dev/null; then
        print_info "Starting Redis..."
        redis-server --daemonize yes
        sleep 2
        print_success "Redis started"
    else
        print_info "Redis is already running"
    fi

    # Start services
    start_service "gateway" "gateway.gateway"
    sleep 1
    start_service "stt_worker" "stt_worker.worker"
    sleep 1
    start_service "translation_worker" "translation_worker.worker"

    print_success "All services started!"
    print_info "Use './run-services.sh stop' to stop all services"
    print_info ""
    print_info "Health check endpoints:"
    print_info "  Gateway: http://localhost:8080/health"
    print_info "  STT Worker: http://localhost:8081/health"
    print_info "  Translation Worker: http://localhost:8082/health"
    print_info "  WebSocket: ws://localhost:5026"

    # Wait for user input to stop
    print_info "Press Ctrl+C to stop all services..."
    trap 'stop_services' INT
    wait
}

# Function to run services in Docker mode
run_prod() {
    print_info "Starting services in Docker mode..."
    print_info "This will use Docker Compose with development setup"

    # Check if docker and docker-compose are available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi

    cd infra

    # Start services with Docker Compose
    print_info "Starting Docker services..."
    docker-compose up -d

    print_success "Services started with Docker Compose!"
    print_info "Use 'docker-compose logs -f' to view logs"
    print_info "Use 'docker-compose down' to stop services"
    print_info ""
    print_info "Health check endpoints:"
    print_info "  Gateway: http://localhost:8080/health"
    print_info "  STT Worker: http://localhost:8081/health"
    print_info "  Translation Worker: http://localhost:8082/health"
    print_info "  WebSocket: ws://localhost:5026"
}

# Function to stop services
stop_services() {
    print_info "Stopping all services..."

    # Stop background processes
    for service in gateway stt_worker translation_worker; do
        if [ -f "${service}.pid" ]; then
            pid=$(cat "${service}.pid")
            if kill -0 $pid 2>/dev/null; then
                print_info "Stopping ${service} (PID: ${pid})..."
                kill $pid
                wait $pid 2>/dev/null || true
                print_success "${service} stopped"
            fi
            rm -f "${service}.pid"
        fi
    done

    # Stop Redis if we started it
    if pgrep -x "redis-server" > /dev/null; then
        print_info "Stopping Redis..."
        pkill redis-server
        print_success "Redis stopped"
    fi

    # Deactivate conda environment if it was activated
    if command -v conda &> /dev/null && [ -n "${CONDA_DEFAULT_ENV}" ]; then
        print_info "Deactivating conda environment..."
        # Source conda activation script and deactivate
        CONDA_BASE=$(conda info --base)
        source "${CONDA_BASE}/etc/profile.d/conda.sh"
        conda deactivate
    fi

    print_success "All services stopped!"
    exit 0
}

# Function to show status
show_status() {
    print_info "Service Status:"

    # Check Redis
    if pgrep -x "redis-server" > /dev/null; then
        echo -e "  ${GREEN}Redis:${NC} Running"
    else
        echo -e "  ${RED}Redis:${NC} Not running"
    fi

    # Check services
    for service in gateway stt_worker translation_worker; do
        if [ -f "${service}.pid" ]; then
            pid=$(cat "${service}.pid")
            if kill -0 $pid 2>/dev/null; then
                echo -e "  ${GREEN}${service}:${NC} Running (PID: ${pid})"
            else
                echo -e "  ${RED}${service}:${NC} Process dead (PID: ${pid})"
                rm -f "${service}.pid"
            fi
        else
            echo -e "  ${RED}${service}:${NC} Not running"
        fi
    done

    echo ""
    print_info "Health check endpoints:"
    print_info "  Gateway: http://localhost:8080/health"
    print_info "  STT Worker: http://localhost:8081/health"
    print_info "  Translation Worker: http://localhost:8082/health"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  dev      Run services in development mode (python -m)"
    echo "  prod     Run services in Docker mode (docker-compose)"
    echo "  stop     Stop all running services"
    echo "  status   Show status of all services"
    echo "  logs     Show logs from all services"
    echo "  restart  Restart all services"
    echo ""
    echo "Examples:"
    echo "  $0 dev      # Start development services"
    echo "  $0 prod     # Start Docker services"
    echo "  $0 stop     # Stop all services"
    echo "  $0 status   # Check service status"
}

# Function to show logs
show_logs() {
    print_info "Showing logs from all services..."

    for service in gateway stt_worker translation_worker; do
        if [ -f "${service}.log" ]; then
            echo ""
            echo "=== ${service} logs ==="
            tail -n 20 "${service}.log"
        else
            echo ""
            echo "=== ${service} logs ==="
            echo "No log file found for ${service}"
        fi
    done
}

# Function to restart services
restart_services() {
    print_info "Restarting all services..."
    stop_services
    sleep 2
    run_dev
}

# Main script logic
MODE=${1:-dev}

case $MODE in
    dev)
        check_env
        run_dev
        ;;
    prod)
        check_env
        run_prod
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    restart)
        restart_services
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
