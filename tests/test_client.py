import requests
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_transcript(video_id, server_url="http://localhost:5001"):
    """Test the transcript endpoint with the given video ID"""
    logger.info(f"Testing transcript for video ID: {video_id}")
    
    # Make the request
    response = requests.get(f"{server_url}/transcript", params={"video_id": video_id})
    
    # Check response
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Got response with status code {response.status_code}")
        logger.info(f"Transcript source: {result.get('source', 'unknown')}")
        logger.info(f"Transcript language: {result.get('language', 'unknown')}")
        
        # Print a snippet of the transcript
        transcript = result.get('transcript', '')
        snippet = transcript[:100] + "..." if len(transcript) > 100 else transcript
        logger.info(f"Transcript snippet: {snippet}")
        logger.info(f"Transcript length: {len(transcript)} characters")
        
        return result
    else:
        logger.error(f"Error: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    # Test with the video ID that has "Caption is updating..."
    test_transcript("kx6N9XbOLXw")