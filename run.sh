#!/bin/bash

# Telegram Gemini Bot Runner Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install it first:"
        echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    print_status "uv is installed"
}

# Check if config file exists
check_config() {
    if [ ! -f "config.json" ]; then
        print_warning "config.json not found. Creating from template..."
        if [ -f "config.json.example" ]; then
            cp config.json.example config.json
        else
            print_error "Please create config.json file with your tokens and API keys"
            exit 1
        fi
    fi
    print_status "Configuration file found"
}

# Install dependencies
install_deps() {
    print_status "Installing dependencies..."
    uv sync --no-editable
    print_status "Dependencies installed"
}

# Run the bot
run_bot() {
    local mode=${1:-"dev"}
    
    if [ "$mode" = "prod" ]; then
        print_status "Starting bot in production mode..."
        uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}
    elif [ "$mode" = "dev" ]; then
        print_status "Starting bot in development mode..."
        uv run python main.py
    else
        print_error "Invalid mode. Use 'dev' or 'prod'"
        exit 1
    fi
}

# Health check
health_check() {
    local port=${PORT:-8000}
    local max_attempts=30
    local attempt=1
    
    print_status "Performing health check..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            print_status "Bot is healthy and running!"
            return 0
        fi
        
        sleep 1
        attempt=$((attempt + 1))
    done
    
    print_error "Health check failed after $max_attempts attempts"
    return 1
}

# Clean up function
cleanup() {
    print_status "Cleaning up..."
    # Kill any background processes if needed
    # Add cleanup logic here
}

# Setup function
setup() {
    print_status "Setting up Telegram Gemini Bot..."
    
    check_uv
    install_deps
    check_config
    
    print_status "Setup complete!"
    print_warning "Don't forget to:"
    echo "1. Update config.json with your Telegram Bot Token"
    echo "2. Update config.json with your Gemini API Key"
    echo "3. Set your webhook URL for production"
}

# Show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  setup           Set up the bot (install dependencies, check config)"
    echo "  dev             Run in development mode (default)"
    echo "  prod            Run in production mode"
    echo "  health          Perform health check"
    echo "  clean           Clean up temporary files"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup        # Initial setup"
    echo "  $0 dev          # Run in development mode"
    echo "  $0 prod         # Run in production mode"
    echo "  $0 health       # Check if bot is running"
    echo ""
    echo "Environment Variables:"
    echo "  PORT            Server port (default: 8000)"
    echo "  WORKERS         Number of workers for production (default: 1)"
    echo "  LOG_LEVEL       Logging level (default: INFO)"
}

# Main script logic
main() {
    local command=${1:-"dev"}
    
    case $command in
        "setup")
            setup
            ;;
        "dev")
            check_uv
            check_config
            run_bot "dev"
            ;;
        "prod")
            check_uv
            check_config
            run_bot "prod"
            ;;
        "health")
            health_check
            ;;
        "clean")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Trap cleanup function on script exit
trap cleanup EXIT

# Run main function with all arguments
main "$@"