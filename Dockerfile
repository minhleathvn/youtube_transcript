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
ENV FLASK_APP=app.flask_server
ENV FLASK_DEBUG=0
ENV PORT=5001

EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Create a non-root user to run the application
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app /tmp/youtube_transcripts
USER appuser

# Set default server based on SERVER_TYPE environment variable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# By default, run the Flask HTTP API server
# To run MCP server, set SERVER_TYPE=mcp when running the container
# docker run -p 5001:5001 -e SERVER_TYPE=mcp youtube-transcript
CMD ["/app/entrypoint.sh"]