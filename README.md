# YouTube Transcript API Server

A server that provides YouTube video transcriptions with special focus on Vietnamese and English languages. Supports both HTTP API and MCP (Model Context Protocol) for integrating with LLM applications.

## Features

- Fetches transcripts directly from YouTube API when available
- Prioritizes Vietnamese and English transcripts
- Fallback to manual audio extraction and transcription when no transcript is available
- Uses OpenAI's Whisper model for high-quality speech recognition
- Supports language specification and detection
- Automatic cleanup of temporary files
- MCP support for integration with Claude Desktop and other MCP clients

## Setup

### Prerequisites
- Python 3.9+
- FFmpeg (required for audio processing)
- Docker (optional)

### Installation

1. Clone the repository:
```
git clone https://github.com/minhleathvn/youtube_transcript.git
cd youtube_transcript
```

2. Install FFmpeg:
   - On macOS: `brew install ffmpeg`
   - On Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - On Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)

3. Install Python dependencies:
```
pip install -r requirements.txt
```

## Running the Server

### HTTP API Server

Run the HTTP API server with:

```
python server.py
```

### MCP Server

Run the MCP server with:

```
python mcp_server.py
```

For development and testing with the MCP Inspector:

```
mcp dev mcp_server.py
```

To install the MCP server in Claude Desktop:

```
mcp install mcp_server.py
```

### Docker

To run the HTTP API server using Docker (recommended for production):

```
docker build -t youtube-transcript .
docker run -p 5000:5000 youtube-transcript
```

## HTTP API Usage

Make a GET request to the `/transcript` endpoint with the following parameters:

```
GET http://localhost:5000/transcript?video_id=VIDEO_ID&language=LANGUAGE&force_extract=false
```

### Parameters

- `video_id` (required): The YouTube video ID (e.g., `dQw4w9WgXcQ` from the URL `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
- `language` (optional): Preferred language for the transcript ('en' or 'vi')
- `force_extract` (optional): Set to 'true' to force manual extraction even if YouTube transcripts exist

### Example Response

```json
{
  "video_id": "dQw4w9WgXcQ",
  "transcript": "We're no strangers to love You know the rules and so do I...",
  "language": "en",
  "source": "youtube_api"
}
```

The `source` field indicates whether the transcript was obtained from the YouTube API (`youtube_api`) or extracted manually using Whisper (`whisper_extraction`).

### Health Check

Check if the HTTP server is running:

```
GET http://localhost:5000/health
```

## MCP Server Features

The MCP server provides the following capabilities that can be accessed through Claude Desktop or other MCP clients:

### Resources

- `youtube://{video_id}/info` - Get basic information about a YouTube video
- `youtube://{video_id}/transcript` - Get the transcript for a YouTube video

### Tools

- `get_transcript(video_id, language)` - Retrieve a transcript from YouTube API
- `extract_transcript(video_id, language)` - Download and transcribe the audio when no API transcript is available
- `search_youtube_video(search_query)` - Search for YouTube videos and return top results

### Prompts

- `transcript_youtube_video(video_url_or_id)` - Get and summarize a transcript from a YouTube video
- `vietnamese_youtube_summary(video_url_or_id)` - Get a Vietnamese summary of a YouTube video

## Language Support

The service prioritizes transcripts in the following order:
1. The user-requested language (if specified)
2. English or Vietnamese (depending on the request)
3. Any available language (auto-detected)
4. Manual extraction and transcription using Whisper

## Performance Considerations

- The first request that requires Whisper might be slow as the model needs to be loaded
- Subsequent requests will be faster as the model remains in memory
- Temporary audio files are automatically cleaned up after processing and files older than 1 hour are removed

## Error Handling

If the video ID is missing or invalid:
```json
{
  "error": "Missing video_id parameter"
}
```

If the transcript can't be retrieved:
```json
{
  "error": "Failed to get transcript: [error message]"
}
```
