#!/usr/bin/env python3
"""
Quick test script for YouTube Transcript service
Used to quickly verify functionality without running full test suite
"""
import argparse
import logging
import sys
import requests
import json
from typing import Optional, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_http_api(video_id: str, server_url: str = "http://localhost:5001", force_extract: bool = False) -> bool:
    """Test the HTTP API server with a specific video ID"""
    logger.info(f"Testing HTTP API for video ID: {video_id}")
    
    # First check server health
    try:
        logger.info(f"Checking server health at {server_url}/health")
        response = requests.get(f"{server_url}/health", timeout=2)
        if response.status_code == 200:
            logger.info("Server is healthy")
        else:
            logger.error(f"Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error connecting to server at {server_url}: {str(e)}")
        logger.error("Make sure the server is running")
        return False
    
    # Get video info
    try:
        logger.info("Getting video info...")
        response = requests.get(f"{server_url}/video/info", params={"video_id": video_id})
        if response.status_code == 200:
            info = response.json()
            logger.info(f"Video title: {info.get('title', 'Unknown')}")
            logger.info(f"Video author: {info.get('author', 'Unknown')}")
            logger.info(f"Video length: {info.get('length', 'Unknown')} seconds")
        else:
            logger.warning(f"Failed to get video info: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
    
    # Get transcript
    try:
        params = {"video_id": video_id}
        if force_extract:
            params["force_extract"] = "true"
            logger.info("Requesting transcript with forced extraction (may take longer)...")
        else:
            logger.info("Requesting transcript...")
        
        response = requests.get(f"{server_url}/transcript", params=params, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Success! Source: {result.get('source', 'unknown')}")
            logger.info(f"Language: {result.get('language', 'unknown')}")
            
            transcript = result.get('transcript', '')
            logger.info(f"Length: {len(transcript)} characters")
            
            # Print snippet
            snippet = transcript[:150] + "..." if len(transcript) > 150 else transcript
            logger.info(f"Snippet: {snippet}")
            
            return True
        else:
            logger.error(f"Failed to get transcript: {response.status_code}")
            logger.error(response.text)
            return False
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        return False

def test_problematic_video():
    """Test with a known problematic video that has placeholder transcript"""
    video_id = "kx6N9XbOLXw"
    logger.info(f"Testing with known problematic video ID: {video_id}")
    logger.info("This video has a placeholder 'caption is updating' transcript")
    logger.info("The server should handle this case properly by falling back to extraction")
    
    return test_http_api(video_id)

def test_normal_video():
    """Test with a known good video that has proper transcript"""
    video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    logger.info(f"Testing with known good video ID: {video_id}")
    logger.info("This video has proper transcripts available")
    logger.info("The server should get the transcript directly from YouTube API")
    
    return test_http_api(video_id)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Quick test for YouTube Transcript service")
    parser.add_argument("--server-url", default="http://localhost:5001", help="Server URL")
    parser.add_argument("--video-id", help="Specific YouTube video ID to test")
    parser.add_argument("--force-extract", action="store_true", help="Force extraction even if transcript exists")
    parser.add_argument("--test-all", action="store_true", help="Run all predefined tests")
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    logger.info("YouTube Transcript Quick Test")
    logger.info(f"Server URL: {args.server_url}")
    
    if args.video_id:
        # Test with specific video ID
        success = test_http_api(args.video_id, args.server_url, args.force_extract)
    elif args.test_all:
        # Run all predefined tests
        logger.info("\n==== Testing Problematic Video ====")
        problematic_success = test_problematic_video()
        
        logger.info("\n==== Testing Normal Video ====")
        normal_success = test_normal_video()
        
        success = problematic_success and normal_success
    else:
        # Default to testing a known good video
        success = test_normal_video()
    
    if success:
        logger.info("Test completed successfully!")
        return 0
    else:
        logger.error("Test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())