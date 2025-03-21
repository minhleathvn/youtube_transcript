import logging
import asyncio
import json
from datetime import datetime
import re
from typing import Dict, Any, Optional

try:
    from mcp.client import Client
except ImportError:
    print("Please install MCP client with: pip install mcp")
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPTester:
    """Test client for the YouTube Transcript MCP server"""
    
    def __init__(self, server_url="http://localhost:5001"):
        self.server_url = server_url
        self.client = None
    
    async def connect(self):
        """Connect to the MCP server"""
        logger.info(f"Connecting to MCP server at {self.server_url}")
        self.client = Client()
        await self.client.connect(self.server_url)
        logger.info("Connected to MCP server")
        
        # Print server info
        server_info = await self.client.server_info()
        logger.info(f"Server name: {server_info['name']}")
        logger.info(f"Server description: {server_info['description']}")
        logger.info(f"API version: {server_info['api_version']}")
        
        # List available features
        await self.print_available_features()
    
    async def print_available_features(self):
        """Print available tools, resources and prompts"""
        if not self.client:
            logger.error("Not connected to MCP server")
            return
        
        # Get available tools
        tools = await self.client.list_tools()
        logger.info(f"Available tools ({len(tools)}):")
        for tool in tools:
            logger.info(f"  - {tool['name']}: {tool['description']}")
        
        # Get available resources
        resources = await self.client.list_resources()
        logger.info(f"Available resources ({len(resources)}):")
        for resource in resources:
            logger.info(f"  - {resource['pattern']}")
        
        # Get available prompts
        prompts = await self.client.list_prompts()
        logger.info(f"Available prompts ({len(prompts)}):")
        for prompt in prompts:
            logger.info(f"  - {prompt['name']}: {prompt['description']}")
    
    async def test_video_info_resource(self, video_id: str):
        """Test the video info resource"""
        logger.info(f"Testing video info resource for video ID: {video_id}")
        
        try:
            resource_uri = f"youtube://{video_id}/info"
            info = await self.client.get_resource(resource_uri)
            logger.info(f"Video info: {info}")
            return info
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return None
    
    async def test_transcript_resource(self, video_id: str):
        """Test the transcript resource"""
        logger.info(f"Testing transcript resource for video ID: {video_id}")
        
        try:
            resource_uri = f"youtube://{video_id}/transcript"
            transcript = await self.client.get_resource(resource_uri)
            
            # Print truncated transcript
            if transcript:
                lines = transcript.split('\n')
                header_lines = [line for line in lines[:5] if line.startswith('#')]
                for line in header_lines:
                    logger.info(line)
                
                # Print first 100 characters of content
                content = '\n'.join([line for line in lines if not line.startswith('#')])
                snippet = content[:100] + "..." if len(content) > 100 else content
                logger.info(f"Transcript snippet: {snippet}")
                logger.info(f"Transcript total length: {len(transcript)} characters")
            else:
                logger.info("No transcript returned from resource")
            
            return transcript
        except Exception as e:
            logger.error(f"Error getting transcript resource: {str(e)}")
            return None
    
    async def test_get_transcript_tool(self, video_id: str, language: Optional[str] = None):
        """Test the get_transcript tool"""
        logger.info(f"Testing get_transcript tool for video ID: {video_id}")
        
        try:
            params = {"video_id": video_id}
            if language:
                params["language"] = language
            
            result = await self.client.use_tool("get_transcript", params, progress_callback=self.progress_callback)
            
            # Print the result
            if result:
                lines = result.split('\n')
                header_lines = lines[:4]  # First few lines with metadata
                for line in header_lines:
                    logger.info(line)
                
                # Print first 100 characters of content
                content = '\n'.join(lines[4:])
                snippet = content[:100] + "..." if len(content) > 100 else content
                logger.info(f"Transcript snippet: {snippet}")
                logger.info(f"Transcript total length: {len(result)} characters")
            else:
                logger.info("No transcript returned from tool")
            
            return result
        except Exception as e:
            logger.error(f"Error using get_transcript tool: {str(e)}")
            return None
    
    async def test_extract_transcript_tool(self, video_id: str, language: Optional[str] = None):
        """Test the extract_transcript tool"""
        logger.info(f"Testing extract_transcript tool for video ID: {video_id}")
        
        try:
            params = {"video_id": video_id}
            if language:
                params["language"] = language
            
            result = await self.client.use_tool("extract_transcript", params, progress_callback=self.progress_callback)
            
            # Print the result
            if result:
                lines = result.split('\n')
                header_lines = lines[:4]  # First few lines with metadata
                for line in header_lines:
                    logger.info(line)
                
                # Print first 100 characters of content
                content = '\n'.join(lines[4:])
                snippet = content[:100] + "..." if len(content) > 100 else content
                logger.info(f"Transcript snippet: {snippet}")
                logger.info(f"Transcript total length: {len(result)} characters")
            else:
                logger.info("No transcript returned from tool")
            
            return result
        except Exception as e:
            logger.error(f"Error using extract_transcript tool: {str(e)}")
            return None
    
    async def test_search_youtube_video_tool(self, search_query: str):
        """Test the search_youtube_video tool"""
        logger.info(f"Testing search_youtube_video tool with query: {search_query}")
        
        try:
            result = await self.client.use_tool("search_youtube_video", {"search_query": search_query})
            logger.info(f"Search results: {result}")
            return result
        except Exception as e:
            logger.error(f"Error using search_youtube_video tool: {str(e)}")
            return None
    
    async def test_transcript_youtube_video_prompt(self, video_url_or_id: str):
        """Test the transcript_youtube_video prompt"""
        logger.info(f"Testing transcript_youtube_video prompt with: {video_url_or_id}")
        
        try:
            prompt = await self.client.use_prompt("transcript_youtube_video", {"video_url_or_id": video_url_or_id})
            logger.info(f"Prompt: {prompt}")
            return prompt
        except Exception as e:
            logger.error(f"Error using transcript_youtube_video prompt: {str(e)}")
            return None
    
    async def progress_callback(self, progress: Dict[str, Any]):
        """Handle progress updates from tool calls"""
        current = progress.get("current", 0)
        total = progress.get("total", 1)
        percent = (current / total) * 100 if total else 0
        
        logger.info(f"Progress: {current}/{total} ({percent:.1f}%)")
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from MCP server")
    
    async def run_tests(self, video_id: str):
        """Run all tests with the given video ID"""
        try:
            # Connect to the server
            await self.connect()
            
            # Run tests
            logger.info(f"\n{'='*50}\nTesting with video ID: {video_id}\n{'='*50}")
            
            # Test video info
            await self.test_video_info_resource(video_id)
            
            # Test transcript resource
            await self.test_transcript_resource(video_id)
            
            # Test get_transcript tool
            await self.test_get_transcript_tool(video_id)
            
            # Test extract_transcript tool
            await self.test_extract_transcript_tool(video_id)
            
            # Test search functionality with the video title
            # Extract title from video info
            info = await self.test_video_info_resource(video_id)
            if info:
                # Extract title from info text
                title_match = re.search(r'Title: (.*)', info)
                if title_match:
                    title = title_match.group(1).strip()
                    # Use first few words as search query
                    search_words = title.split()[:3]
                    search_query = ' '.join(search_words)
                    await self.test_search_youtube_video_tool(search_query)
            
            # Test prompt (optional as it might take longer)
            # await self.test_transcript_youtube_video_prompt(video_id)
            
        finally:
            # Disconnect
            await self.disconnect()

async def main():
    """Main entry point for the MCP tester"""
    # Create a timestamp for the test run
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Starting MCP server test run at {timestamp}")
    
    # Create the tester
    tester = MCPTester()
    
    # Test with the video ID that has "Caption is updating..."
    await tester.run_tests("kx6N9XbOLXw")
    
    # Test with a video known to have good transcripts
    logger.info("\n\nTrying with a different video for comparison:")
    await tester.run_tests("dQw4w9WgXcQ")  # Rick Astley - Never Gonna Give You Up

if __name__ == "__main__":
    asyncio.run(main())