#!/bin/bash

# Simple Docker run script for SSNS Flask Application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p data logs
    print_status "Directories created successfully"
}

# Function to build the Docker image
build_image() {
    print_status "Building Docker image..."
    docker build -t ssns-flask-app .
    print_status "Docker image built successfully"
}

# Function to run the container
run_container() {
    print_status "Starting the application..."
    docker run -d \
        --name ssns-flask-app \
        -p 8000:8000 \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        -e DB_PATH=/app/data/environmental_data.db \
        -e SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-production} \
        ssns-flask-app
    
    print_status "Application started successfully!"
    print_status "Access the application at: http://localhost:8000"
    print_status "Health check endpoint: http://localhost:8000/api/health"
}

# Function to stop the container
stop_container() {
    print_status "Stopping the application..."
    docker stop ssns-flask-app 2>/dev/null || true
    docker rm ssns-flask-app 2>/dev/null || true
    print_status "Application stopped successfully"
}

# Function to view logs
view_logs() {
    print_status "Showing application logs..."
    docker logs -f ssns-flask-app
}

# Function to show status
show_status() {
    print_status "Application status:"
    docker ps -a --filter name=ssns-flask-app
    echo ""
    if docker ps --filter name=ssns-flask-app --filter status=running | grep -q ssns-flask-app; then
        print_status "Recent logs:"
        docker logs --tail=20 ssns-flask-app
    else
        print_warning "Container is not running"
    fi
}

# Function to clean up
cleanup() {
    print_warning "This will remove the container and image. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up..."
        stop_container
        docker rmi ssns-flask-app 2>/dev/null || true
        print_status "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Function to restart the application
restart_app() {
    stop_container
    run_container
}

# Main script logic
case "${1:-start}" in
    "start")
        check_docker
        create_directories
        build_image
        run_container
        ;;
    "stop")
        check_docker
        stop_container
        ;;
    "restart")
        check_docker
        restart_app
        ;;
    "logs")
        check_docker
        view_logs
        ;;
    "status")
        check_docker
        show_status
        ;;
    "cleanup")
        check_docker
        cleanup
        ;;
    "build")
        check_docker
        build_image
        ;;
    "run")
        check_docker
        create_directories
        run_container
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|cleanup|build|run}"
        echo ""
        echo "Commands:"
        echo "  start   - Build and start the application (default)"
        echo "  stop    - Stop the application"
        echo "  restart - Restart the application"
        echo "  logs    - View application logs"
        echo "  status  - Show application status"
        echo "  cleanup - Remove container and image"
        echo "  build   - Build the Docker image only"
        echo "  run     - Run the container (assumes image is built)"
        exit 1
        ;;
esac 