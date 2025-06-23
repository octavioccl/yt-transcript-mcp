FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies directly with pip
COPY pyproject.toml ./

# Extract dependencies from pyproject.toml and install with pip
RUN pip install --no-cache-dir \
    "mcp>=0.9.0" \
    "youtube-transcript-api>=0.6.2" \
    "requests>=2.31.0"

# Copy application code
COPY src/youtube_transcript_mcp_server.py ./

# Create non-root user
RUN groupadd -r mcp && useradd -r -g mcp mcp
RUN chown -R mcp:mcp /app
USER mcp

# Expose port (for potential HTTP transport)
EXPOSE 8000

# Default command - run with stdio transport
CMD ["python", "youtube_transcript_mcp_server.py"] 