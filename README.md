# YouTube Transcript API

A Python service that provides APIs to fetch and transcribe YouTube video content. It supports both REST API (Flask) and MCP server implementations.

## Features

- Fetch YouTube video transcripts in multiple languages (English and Vietnamese)
- Auto-detect and use available transcripts
- Fallback to audio transcription using Whisper when transcripts are unavailable
- Support for both REST API and MCP server interfaces
- Automatic language detection
- Temporary file cleanup
- Progress reporting for long-running operations

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### REST API (Flask)

Start the Flask server:
```bash
python apps/flask_server.py
```

Available endpoints:
- `GET /transcript?video_id=<video_id>&language=<lang>` - Get video transcript
- `GET /video/info?video_id=<video_id>` - Get video information
- `GET /health` - Health check endpoint

### MCP Server

Start the MCP server:
```bash
python apps/mcp_server.py
```

Available tools:
- `get_transcript(video_id, language)` - Get video transcript
- `extract_transcript(video_id, language)` - Extract transcript from audio
- `search_youtube_video(query)` - Search for YouTube videos

## Language Support

- English (en)
- Vietnamese (vi)
- Auto-detection for other languages

## Dependencies

- youtube-transcript-api
- pytube
- whisper
- torch
- langdetect
- flask (for REST API)
- mcp (for MCP server)

## Development

The project structure:
```
apps/
├── __init__.py
├── flask_server.py  # REST API implementation
├── mcp_server.py    # MCP server implementation
└── utils.py         # Shared utilities
```

## License

MIT License
