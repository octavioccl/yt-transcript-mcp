# YouTube Transcript MCP Server

A Model Context Protocol (MCP) server that extracts transcripts from YouTube videos. This server provides English transcripts by default and is designed to give LLMs easy access to YouTube video content.

## Project Structure

```
yt-transcript-mcp/
├── src/                           # Source code
│   ├── __init__.py
│   └── youtube_transcript_mcp_server.py  # Main server
├── tests/                         # Test files
│   ├── __init__.py
│   └── test_server.py
├── docker/                        # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .dockerignore
├── config/                        # MCP configurations
│   ├── mcp.json                   # Local Poetry config
│   └── mcp-docker.json           # Docker config
├── docs/                          # Documentation
│   ├── README.md
│   └── LICENSE
├── scripts/                       # Utility scripts
│   ├── run_tests.py              # Test runner
│   └── build_docker.py           # Docker builder
├── pyproject.toml                 # Project dependencies
├── poetry.lock                    # Locked dependencies
├── poetry.toml                    # Poetry config
└── .gitignore                     # Git ignore rules
```

## Features

- Extract transcripts from YouTube videos via URL or video ID
- Prioritizes English transcripts by default
- Supports multiple output formats (text, JSON, raw)
- Lists available transcript languages
- Comprehensive error handling
- Docker support for easy deployment
- Both stdio and HTTP transport options

## Installation

### Using Poetry (Local Development)

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run the server
python src/youtube_transcript_mcp_server.py
```

### Using Docker (Recommended)

```bash
# Build and run with Docker Compose
cd docker && docker-compose up --build

# Or use the build script
python scripts/build_docker.py
docker run -p 8000:8000 youtube-transcript-mcp
```

## Usage

### MCP Tools

The server provides three main tools:

#### 1. `get_transcript_from_url`
Extract transcript from a YouTube URL.

```python
# Example usage in MCP client
result = await client.call_tool("get_transcript_from_url", {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "language": "en",  # Optional, defaults to "en"
    "format_type": "text"  # Optional: "text", "json", or "raw"
})
```

#### 2. `get_transcript_from_id`
Extract transcript using video ID directly.

```python
result = await client.call_tool("get_transcript_from_id", {
    "video_id": "dQw4w9WgXcQ",
    "language": "en",
    "format_type": "text"
})
```

#### 3. `list_available_transcripts`
List all available transcript languages for a video.

```python
result = await client.call_tool("list_available_transcripts", {
    "video_url_or_id": "dQw4w9WgXcQ"
})
```

### MCP Resources

The server also provides a resource endpoint:

```
youtube://transcript/{video_id}
```

### Language Priority

The server implements intelligent language fallback:

1. **Requested language** (parameter, defaults to "en")
2. **English ("en")** if requested language unavailable
3. **Any available language** if English unavailable

### Output Formats

- **text** (default): Formatted transcript with timestamps `[MM:SS] text`
- **json**: Structured JSON with segments, timestamps, and metadata
- **raw**: Raw data structure from YouTube API

## Development

### Project Structure Commands

```bash
# Run tests
python scripts/run_tests.py

# Build Docker image
python scripts/build_docker.py --no-cache

# Run tests with Poetry
poetry run python tests/test_server.py
```

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "poetry",
      "args": ["run", "python", "src/youtube_transcript_mcp_server.py"],
      "cwd": "/path/to/yt-transcript-mcp"
    }
  }
}
```

Or use the Docker version:

```json
{
  "mcpServers": {
    "youtube-transcript-docker": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "youtube-transcript-mcp"
      ]
    }
  }
}
```

## Docker Configuration

### Environment Variables

- `MCP_TRANSPORT`: Transport type (`stdio` or `http`, defaults to `stdio`)
- `PYTHONUNBUFFERED`: Set to `1` for real-time logging

### Docker Compose Profiles

```bash
# Run with stdio transport (default)
cd docker && docker-compose up

# Run with HTTP transport
cd docker && docker-compose --profile http up
```

## API Reference

### Error Handling

The server handles various YouTube-specific errors:

- `TranscriptsDisabled`: Video has disabled transcripts
- `VideoUnavailable`: Video doesn't exist or is private
- `NoTranscriptFound`: No transcripts in requested language
- `TooManyRequests`: Rate limiting from YouTube
- `YouTubeURLError`: Invalid URL format

### Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://www.youtube.com/v/VIDEO_ID`

## Examples

### Basic Usage

```bash
# Get transcript for a video
echo '{"method": "tools/call", "params": {"name": "get_transcript_from_url", "arguments": {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}}}' | python src/youtube_transcript_mcp_server.py
```

### Using with FastMCP Client

```python
from fastmcp import Client

async def main():
    client = Client("python src/youtube_transcript_mcp_server.py")
    
    async with client:
        # Get transcript
        result = await client.call_tool("get_transcript_from_url", {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        })
        
        print(result[0].text)

import asyncio
asyncio.run(main())
```

## Testing

```bash
# Run all tests
python scripts/run_tests.py

# Test Docker build
python scripts/build_docker.py --no-cache

# Manual testing
python tests/test_server.py
```

## Limitations

- Requires videos to have available transcripts
- Subject to YouTube's rate limiting
- Some videos may have transcripts disabled by creators
- IP blocking may occur with heavy usage (consider proxy solutions)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run tests: `python scripts/run_tests.py`
6. Submit a pull request

## License

This project is licensed under the MIT License. See `docs/LICENSE` for details.

## References

- [Model Context Protocol](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://gofastmcp.com)
- [YouTube Transcript API](https://github.com/jdepoix/youtube-transcript-api)
- [MCP Servers Repository](https://github.com/docker/mcp-servers) 