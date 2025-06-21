FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and Pipfile.lock first (for better Docker layer caching)
COPY Pipfile Pipfile.lock ./

# Configure pipenv environment variables
ENV PIPENV_VENV_IN_PROJECT=1
ENV PIPENV_DONT_LOAD_ENV=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install dependencies using pipenv
# --deploy ensures we use the lock file exactly as specified
# --system installs packages to system Python (no virtual env needed in container)
RUN pipenv install --deploy --system --ignore-pipfile

# Copy application code
COPY . .

# Create audio temp directory with proper permissions
RUN mkdir -p /tmp/therapist_copilot && chmod 755 /tmp/therapist_copilot

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
RUN chown -R appuser:appuser /app && chown -R appuser:appuser /tmp/therapist_copilot

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]