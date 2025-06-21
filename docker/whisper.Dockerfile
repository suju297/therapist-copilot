FROM alpine:3.18

# Install dependencies
RUN apk add --no-cache \
    curl \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    g++ \
    make \
    cmake \
    git \
    pkgconfig \
    openblas-dev \
    && pip3 install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    numpy

# Create working directory
WORKDIR /app

# Clone and build whisper.cpp
RUN git clone https://github.com/ggerganov/whisper.cpp.git \
    && cd whisper.cpp \
    && make \
    && cp main /usr/local/bin/whisper \
    && cp server /usr/local/bin/whisper-server

# Create models directory
RUN mkdir -p /models

# Copy Python server script
COPY docker/whisper_server.py .

# Make it executable
RUN chmod +x whisper_server.py

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start server
CMD ["python3", "whisper_server.py"]