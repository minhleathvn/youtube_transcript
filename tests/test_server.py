#!/usr/bin/env python3
import requests
import argparse
import json
import sys

def test_transcript_api(video_id, language=None, force_extract=False, info=False, server_url="http://localhost:5002"):
    """Test the transcript API with the given parameters"""
    
    # Build request URL based on action
    if info:
        url = f"{server_url}/video/info?video_id={video_id}"
        print(f"Getting video info from: {url}")
    else:
        url = f"{server_url}/transcript?video_id={video_id}"
        if language:
            url += f"&language={language}"
        if force_extract:
            url += "&force_extract=true"
        print(f"Getting transcript from: {url}")
    
    try:
        # Make the request with a longer timeout for manual extraction
        response = requests.get(url, timeout=120)
        
        # Check if successful
        if response.status_code == 200:
            data = response.json()
            
            if info:
                # Display video info
                print("\n=== VIDEO INFO ===")
                for key, value in data.items():
                    print(f"{key}: {value}")
            else:
                # Display transcript info
                print("\n=== TRANSCRIPT INFO ===")
                print(f"Video ID: {data.get('video_id')}")
                print(f"Language: {data.get('language')}")
                print(f"Source: {data.get('source')}")
                print("\n=== TRANSCRIPT TEXT ===")
                # Print first 500 characters of transcript
                transcript = data.get('transcript', '')
                preview_length = min(500, len(transcript))
                print(f"{transcript[:preview_length]}...")
                print(f"\nTotal length: {len(transcript)} characters")
        else:
            print(f"Error: {response.status_code}")
            print(response.json())
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

def check_server_health(server_url="http://localhost:5002"):
    """Check if the server is running and healthy"""
    try:
        url = f"{server_url}/health"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print(f"Server at {server_url} is healthy!")
            print(response.json())
            return True
        else:
            print(f"Server returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error connecting to server: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test YouTube Transcript API Server")
    parser.add_argument("--video-id", "-v", help="YouTube video ID")
    parser.add_argument("--language", "-l", help="Preferred language (en or vi)")
    parser.add_argument("--force-extract", "-f", action="store_true", help="Force manual extraction")
    parser.add_argument("--info", "-i", action="store_true", help="Get video info instead of transcript")
    parser.add_argument("--health", action="store_true", help="Check server health")
    parser.add_argument("--server", "-s", default="http://localhost:5002", help="Server URL")
    
    args = parser.parse_args()
    
    if args.health:
        check_server_health(args.server)
        sys.exit(0)
    
    if not args.video_id:
        parser.error("--video-id is required unless --health is specified")
    
    sys.exit(test_transcript_api(
        args.video_id,
        args.language,
        args.force_extract,
        args.info,
        args.server
    ))