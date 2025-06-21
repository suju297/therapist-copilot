#!/bin/bash

# Simple start script for Therapist Copilot (Transcription + Risk Assessment only)
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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

echo "🚀 Starting Simplified Therapist Copilot"
echo "========================================"
echo "Features: Real-time Transcription + Risk Assessment"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create one with your Gemini API key."
    echo "Required variables:"
    echo "  - GEMINI_API_KEY=your_api_key_here"
    echo "  - LLM_PROVIDER=gemini"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Verify Gemini API key is set
if ! grep -q "GEMINI_API_KEY=.*[a-zA-Z0-9]" .env; then
    print_warning "GEMINI_API_KEY appears to be empty in .env file"
    echo "Please add your Gemini API key to the .env file"
fi

# Start the simplified service
print_status "Starting simplified API service..."
if docker-compose up -d --build; then
    print_success "API service started successfully!"
else
    print_error "Failed to start API service"
    exit 1
fi

# Wait for service to be ready
print_status "Waiting for API to be ready..."
sleep 10

# Check API health
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    print_success "API is ready and healthy!"
else
    print_warning "API may still be starting up..."
fi

echo ""
print_success "🎉 Simplified Therapist Copilot is running!"
echo ""
echo "📋 Available Services:"
echo "   • Health Check: http://localhost:8000/api/v1/health"
echo "   • STT File Upload: http://localhost:8000/api/v1/stt/transcribe"
echo "   • Risk Assessment: http://localhost:8000/api/v1/risk/assess"
echo "   • WebSocket Audio Stream: ws://localhost:8000/api/v1/ws/audio/{session_id}"
echo "   • API Documentation: http://localhost:8000/docs"
echo ""
echo "🎯 Real-time WebSocket Flow:"
echo "   1. Connect to WebSocket with session ID"
echo "   2. Stream audio chunks in real-time"
echo "   3. Receive live transcriptions"
echo "   4. Get automatic risk assessments"
echo "   5. Receive crisis alerts if needed"
echo ""
echo "📜 Useful commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop service: docker-compose down"
echo "   • Restart: docker-compose restart"
echo "   • Test WebSocket: python demo_websocket_client.py --audio-file test.wav"
echo ""
echo "🔧 What's simplified:"
echo "   ❌ No PostgreSQL database"
echo "   ❌ No vector embeddings"
echo "   ❌ No CBT snippets storage"
echo "   ❌ No SOAP note generation"
echo "   ✅ Real-time transcription via WebSocket"
echo "   ✅ Automatic risk assessment"
echo "   ✅ Crisis detection and alerts"
echo "   ✅ In-memory session management"
echo ""

# Test the WebSocket endpoint
print_status "Testing WebSocket endpoint..."
if command -v python3 &> /dev/null; then
    echo "To test WebSocket streaming:"
    echo "  python3 demo_websocket_client.py --audio-file your_audio.wav"
    echo ""
fi

# Offer to show logs
read -p "Show real-time logs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Press Ctrl+C to stop viewing logs..."
    docker-compose logs -f
fi