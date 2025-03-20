# YouTube Transcript API Server

A microservice that provides YouTube video transcriptions via a simple HTTP API.

## Setup

### Prerequisites
- Python 3.9+
- Docker (optional)

### Installation

1. Clone the repository:
```
git clone https://github.com/minhleathvn/youtube_transcript.git
cd youtube_transcript
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Run the server:
```
python server.py
```

### Docker

To run using Docker:

```
docker build -t youtube-transcript .
docker run -p 5000:5000 youtube-transcript
```

## Usage

Make a GET request to the `/transcript` endpoint with a `video_id` parameter:

```
GET http://localhost:5000/transcript?video_id=VIDEO_ID
```

Where `VIDEO_ID` is the YouTube video ID (e.g., `dQw4w9WgXcQ` from the URL `https://www.youtube.com/watch?v=dQw4w9WgXcQ`).

### Example Response

```json
{
  "video_id": "dQw4w9WgXcQ",
  "transcript": "We're no strangers to love You know the rules and so do I..."
}
```

## Error Handling

If the video ID is missing:
```json
{
  "error": "Missing video_id parameter"
}
```

If the transcript can't be retrieved:
```json
{
  "error": "Error message from YouTube API"
}
```
