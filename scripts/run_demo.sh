#!/bin/bash

# Run demo script for Therapist Copilot
# Starts the full stack and runs a demo session

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
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

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    # Kill background processes if any
    jobs -p | xargs -r kill 2>/dev/null || true
}

trap cleanup EXIT

echo "🎭 Starting Therapist Copilot Demo"
echo "=================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found, copying from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created"
    else
        print_error ".env.example file not found!"
        exit 1
    fi
fi

# Check if models exist
print_status "Checking if models are available..."
if [ ! -d "models" ] || [ -z "$(ls -A models)" ]; then
    print_warning "Models not found. Running model download..."
    ./scripts/pull_models.sh
fi

# Start the stack
print_status "Starting Docker Compose stack..."
if docker-compose up -d; then
    print_success "Stack started successfully"
else
    print_error "Failed to start stack"
    exit 1
fi

# Wait for services to be ready
print_status "Waiting for services to be ready..."

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local url=$2
    local timeout=${3:-60}
    
    print_status "Waiting for $service_name..."
    
    for i in $(seq 1 $timeout); do
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        else
            echo -n "."
            sleep 2
        fi
    done
    
    print_error "$service_name failed to start within ${timeout} seconds"
    return 1
}

# Wait for database
print_status "Waiting for database..."
sleep 5

# Wait for API
wait_for_service "API" "http://localhost:8000/api/v1/health/quick" 30

# Wait for Ollama
wait_for_service "Ollama" "http://localhost:11434/api/tags" 30

# Wait for Whisper
wait_for_service "Whisper" "http://localhost:8001/health" 30

# Load snippets
print_status "Loading CBT snippets..."
if docker-compose run --rm seed python -m seed.load_snippets; then
    print_success "CBT snippets loaded successfully"
else
    print_warning "Failed to load snippets, continuing anyway..."
fi

# Check system health
print_status "Checking system health..."
if curl -s http://localhost:8000/api/v1/health | jq -r '.status' | grep -q "healthy"; then
    print_success "System health check passed"
else
    print_warning "System health check failed, but continuing..."
fi

# Generate demo session ID
DEMO_SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
print_status "Demo session ID: $DEMO_SESSION_ID"

# Check if demo audio exists
DEMO_AUDIO_PATH="demo_assets/session.wav"
if [ ! -f "$DEMO_AUDIO_PATH" ]; then
    print_status "Demo audio not found, it will be generated automatically"
    mkdir -p demo_assets
fi

# Run the demo
print_status "Starting audio demo replay..."
echo ""
echo "🎤 Running Audio Demo"
echo "====================="

if docker-compose exec -T api python -m seed.demo_audio_replay; then
    print_success "Demo completed successfully!"
else
    print_warning "Demo completed with warnings"
fi

# Show results
echo ""
echo "📊 Demo Results"
echo "==============="

# Get session info
print_status "Fetching session information..."
SESSION_INFO=$(curl -s -H "Authorization: Bearer supersecret-dev-token" \
    "http://localhost:8000/api/v1/sessions" | jq -r '.sessions[0] // empty')

if [ -n "$SESSION_INFO" ]; then
    echo "$SESSION_INFO" | jq .
    
    SESSION_ID=$(echo "$SESSION_INFO" | jq -r '.id')
    if [ "$SESSION_ID" != "null" ] && [ -n "$SESSION_ID" ]; then
        print_status "Generating SOAP draft for session..."
        
        DRAFT_RESPONSE=$(curl -s -X POST \
            -H "Authorization: Bearer supersecret-dev-token" \
            -H "Content-Type: application/json" \
            -d '{"force_regenerate": true}' \
            "http://localhost:8000/api/v1/draft/$SESSION_ID")
        
        if echo "$DRAFT_RESPONSE" | jq -e '.draft_generated' > /dev/null 2>&1; then
            print_success "SOAP draft generated!"
            echo ""
            echo "📋 Generated SOAP Note:"
            echo "======================="
            echo "$DRAFT_RESPONSE" | jq -r '.soap_note | to_entries | .[] | "\(.key | ascii_upcase): \(.value)"'
            
            echo ""
            echo "📝 Homework Assignments:"
            echo "========================"
            echo "$DRAFT_RESPONSE" | jq -r '.homework_assignments[]? | "• \(.title): \(.description)"'
        else
            print_warning "Failed to generate SOAP draft"
        fi
    fi
else
    print_warning "No session data found"
fi

# Show useful URLs
echo ""
echo "🔗 Useful URLs"
echo "=============="
echo "• API Documentation: http://localhost:8000/docs"
echo "• Health Check: http://localhost:8000/api/v1/health"
echo "• Sessions List: http://localhost:8000/api/v1/sessions"
echo "• Ollama API: http://localhost:11434"
echo "• Whisper Service: http://localhost:8001"

# Show logs command
echo ""
echo "📜 Useful Commands"
echo "=================="
echo "• View logs: docker-compose logs -f"
echo "• View API logs: docker-compose logs -f api"
echo "• Stop demo: docker-compose down"
echo "• Restart: docker-compose restart"

# Optional: Keep services running
echo ""
read -p "Keep services running for testing? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_success "Services will continue running in the background"
    print_status "Use 'docker-compose down' to stop all services"
    
    # Show real-time logs for a few seconds
    print_status "Showing real-time logs (Ctrl+C to stop)..."
    timeout 10 docker-compose logs -f --tail=20 || true
    
    echo ""
    print_success "Demo completed! Services are running in the background."
else
    print_status "Stopping services..."
    docker-compose down
    print_success "Demo cleanup completed"
fi

echo ""
echo "🎉 Therapist Copilot Demo Finished!"
echo ""