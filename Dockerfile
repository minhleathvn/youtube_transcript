FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including ffmpeg and curl (for healthcheck)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp directory for audio files
RUN mkdir -p /tmp/youtube_transcripts

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Create a non-root user to run the application
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app /tmp/youtube_transcripts
USER appuser

# You can use either the HTTP API server or the MCP server
# Default to HTTP API server
CMD ["python", "server.py"]

# To use MCP server, override the CMD:
# docker run -p 5000:5000 youtube-transcript python mcp_server.py