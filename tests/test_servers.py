#!/usr/bin/env python3
"""
End-to-end testing script for YouTube Transcript servers (both HTTP and MCP)
"""
import os
import logging
import time
import json
import argparse
import subprocess
import signal
import sys
import requests
from typing import Optional, Dict, List, Any, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServerTester:
    """Test runner for YouTube Transcript servers"""
    
    def __init__(self, server_type: str = "http", port: int = 5001, video_ids: List[str] = None):
        self.server_type = server_type.lower()
        self.port = port
        
        # Default test video IDs if none provided
        if not video_ids:
            # First is the problematic one with "Caption is updating..."
            # Second is a well-known video with good transcripts
            self.video_ids = ["kx6N9XbOLXw", "dQw4w9WgXcQ"]
        else:
            self.video_ids = video_ids
        
        self.server_process = None
        self.base_url = f"http://localhost:{port}"
    
    def start_server(self) -> bool:
        """Start the appropriate server for testing"""
        if self.server_process:
            logger.warning("Server is already running")
            return True
        
        try:
            # Determine which server to start
            if self.server_type == "http":
                cmd = ["python", "server.py"]
                environment = os.environ.copy()
            elif self.server_type == "mcp":
                cmd = ["python", "mcp_server.py"]
                environment = os.environ.copy()
            else:
                logger.error(f"Unknown server type: {self.server_type}")
                return False
            
            # Add log messages
            logger.info(f"Starting {self.server_type.upper()} server on port {self.port}...")
            logger.info(f"Command: {' '.join(cmd)}")
            
            # Start the server process
            self.server_process = subprocess.Popen(
                cmd,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start (up to 10 seconds)
            started = False
            for _ in range(10):
                try:
                    # Try to connect to health endpoint
                    if self.server_type == "http":
                        response = requests.get(f"{self.base_url}/health", timeout=1)
                        if response.status_code == 200:
                            started = True
                            break
                    else:  # MCP just try root endpoint
                        response = requests.get(self.base_url, timeout=1)
                        if response.status_code in [200, 404]:  # MCP may return 404 but it's still running
                            started = True
                            break
                except Exception:
                    # Server might not be ready yet
                    pass
                
                # Wait a bit before trying again
                time.sleep(1)
            
            if not started:
                logger.error(f"Failed to start {self.server_type.upper()} server")
                self.stop_server()
                return False
            
            logger.info(f"{self.server_type.upper()} server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting server: {str(e)}")
            return False
    
    def stop_server(self):
        """Stop the running server"""
        if self.server_process:
            logger.info(f"Stopping {self.server_type.upper()} server...")
            
            # Try to terminate gracefully
            self.server_process.terminate()
            
            # Give it a moment to shut down
            time.sleep(2)
            
            # If still running, force kill
            if self.server_process.poll() is None:
                logger.warning("Server did not terminate gracefully, forcing...")
                self.server_process.kill()
            
            # Collect any output
            stdout, stderr = self.server_process.communicate()
            if stdout:
                logger.debug(f"Server stdout: {stdout}")
            if stderr:
                logger.warning(f"Server stderr: {stderr}")
            
            self.server_process = None
            logger.info(f"{self.server_type.upper()} server stopped")
    
    def test_http_server(self, video_id: str) -> bool:
        """Run tests against the HTTP API server"""
        if self.server_type != "http":
            logger.error("This method is only for HTTP server testing")
            return False
        
        logger.info(f"Testing HTTP server with video ID: {video_id}")
        success = True
        
        # Test health endpoint
        try:
            logger.info("Testing health endpoint...")
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                logger.info("Health check successful")
            else:
                logger.error(f"Health check failed: {response.status_code} - {response.text}")
                success = False
        except Exception as e:
            logger.error(f"Error checking health: {str(e)}")
            success = False
        
        # Test video info endpoint
        try:
            logger.info("Testing video info endpoint...")
            response = requests.get(f"{self.base_url}/video/info", params={"video_id": video_id})
            if response.status_code == 200:
                info = response.json()
                logger.info(f"Video title: {info.get('title', 'Unknown')}")
                logger.info(f"Video author: {info.get('author', 'Unknown')}")
                logger.info(f"Video length: {info.get('length', 'Unknown')} seconds")
            else:
                logger.error(f"Video info failed: {response.status_code} - {response.text}")
                success = False
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            success = False
        
        # Test transcript endpoint with default settings
        try:
            logger.info("Testing transcript endpoint (default)...")
            response = requests.get(f"{self.base_url}/transcript", params={"video_id": video_id})
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Transcript source: {result.get('source', 'unknown')}")
                logger.info(f"Transcript language: {result.get('language', 'unknown')}")
                
                # Print a snippet of the transcript
                transcript = result.get('transcript', '')
                snippet = transcript[:100] + "..." if len(transcript) > 100 else transcript
                logger.info(f"Transcript snippet: {snippet}")
                logger.info(f"Transcript length: {len(transcript)} characters")
            else:
                logger.warning(f"Transcript retrieval returned: {response.status_code} - {response.text}")
                # This might not be a failure if video has no transcript
                if "No transcript available" in response.text:
                    logger.warning("No transcript available for this video (expected for some videos)")
                else:
                    success = False
        except Exception as e:
            logger.error(f"Error getting transcript: {str(e)}")
            success = False
        
        # Test transcript endpoint with force extraction
        try:
            logger.info("Testing transcript endpoint (force extraction)...")
            response = requests.get(
                f"{self.base_url}/transcript", 
                params={
                    "video_id": video_id,
                    "force_extract": "true"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Extraction transcript source: {result.get('source', 'unknown')}")
                logger.info(f"Extraction transcript language: {result.get('language', 'unknown')}")
                
                # Print a snippet of the transcript
                transcript = result.get('transcript', '')
                snippet = transcript[:100] + "..." if len(transcript) > 100 else transcript
                logger.info(f"Extraction transcript snippet: {snippet}")
                logger.info(f"Extraction transcript length: {len(transcript)} characters")
            else:
                logger.warning(f"Forced extraction returned: {response.status_code} - {response.text}")
                # This might not be a failure if extraction fails for some reason
                if "Failed to get transcript" in response.text:
                    logger.warning("Extraction failed (may be expected for some videos)")
                else:
                    success = False
        except Exception as e:
            logger.error(f"Error with forced extraction: {str(e)}")
            success = False
        
        return success
    
    def test_mcp_server(self, video_id: str) -> bool:
        """Run tests against the MCP server"""
        if self.server_type != "mcp":
            logger.error("This method is only for MCP server testing")
            return False
        
        logger.info(f"Testing MCP server with video ID: {video_id}")
        
        # We'll use the test_mcp_client.py script for this if it exists
        script_path = os.path.join(os.path.dirname(__file__), "test_mcp_client.py")
        
        if not os.path.exists(script_path):
            logger.error(f"MCP test client script not found at {script_path}")
            return False
        
        try:
            # Run the MCP test client script
            logger.info(f"Running MCP test client script for video ID: {video_id}")
            
            # Prepare command to run the script with the video ID
            cmd = [sys.executable, script_path]
            
            # Execute the test script
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Print the output
            if result.stdout:
                for line in result.stdout.splitlines():
                    logger.info(f"MCP Test: {line}")
            
            # Print any errors
            if result.stderr:
                for line in result.stderr.splitlines():
                    logger.error(f"MCP Test Error: {line}")
            
            # Check if the test was successful
            if result.returncode == 0:
                logger.info("MCP server tests completed successfully")
                return True
            else:
                logger.error(f"MCP server tests failed with return code {result.returncode}")
                return False
            
        except Exception as e:
            logger.error(f"Error running MCP tests: {str(e)}")
            return False
    
    def run_tests(self) -> bool:
        """Run all tests for the specified server type"""
        try:
            # Start the server
            if not self.start_server():
                return False
            
            # Wait a moment for server to fully initialize
            time.sleep(3)
            
            # Run tests for each video ID
            overall_success = True
            for video_id in self.video_ids:
                logger.info(f"\n{'='*50}\nTesting with video ID: {video_id}\n{'='*50}")
                
                if self.server_type == "http":
                    success = self.test_http_server(video_id)
                else:  # mcp
                    success = self.test_mcp_server(video_id)
                
                if not success:
                    overall_success = False
                
                # Log test result
                if success:
                    logger.info(f"Tests for video ID {video_id} completed successfully")
                else:
                    logger.warning(f"Tests for video ID {video_id} had some failures")
            
            return overall_success
            
        finally:
            # Always stop the server when done
            self.stop_server()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test YouTube Transcript servers")
    parser.add_argument(
        "--server-type",
        choices=["http", "mcp", "both"],
        default="both",
        help="Type of server to test (http, mcp, or both)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Port to run the server on"
    )
    parser.add_argument(
        "--video-ids",
        nargs="+",
        help="Video IDs to test with (space-separated)"
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    # Print test run header
    logger.info(f"{'='*80}")
    logger.info(f"YouTube Transcript Server Test Run")
    logger.info(f"Server type: {args.server_type}")
    logger.info(f"Port: {args.port}")
    if args.video_ids:
        logger.info(f"Video IDs: {', '.join(args.video_ids)}")
    logger.info(f"{'='*80}\n")
    
    # Run tests based on server type
    if args.server_type in ["http", "both"]:
        logger.info("\n\nTESTING HTTP SERVER\n\n")
        http_tester = ServerTester("http", args.port, args.video_ids)
        http_success = http_tester.run_tests()
        
        logger.info(f"\nHTTP server tests {'PASSED' if http_success else 'FAILED'}\n")
    
    if args.server_type in ["mcp", "both"]:
        logger.info("\n\nTESTING MCP SERVER\n\n")
        mcp_tester = ServerTester("mcp", args.port, args.video_ids)
        mcp_success = mcp_tester.run_tests()
        
        logger.info(f"\nMCP server tests {'PASSED' if mcp_success else 'FAILED'}\n")
    
    # Print test run footer
    logger.info(f"{'='*80}")
    logger.info(f"YouTube Transcript Server Test Run Completed")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Test run interrupted by user")
        sys.exit(1)