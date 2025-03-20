FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp directory for audio files
RUN mkdir -p /tmp/youtube_transcripts

EXPOSE 5000

# You can use either the HTTP API server or the MCP server
# Default to HTTP API server
CMD ["python", "server.py"]

# To use MCP server:
# CMD ["python", "mcp_server.py"]