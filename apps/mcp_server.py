"""
MCP server for YouTube transcript API
"""
import logging
from typing import Optional
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Search
from langdetect import detect

from apps.utils import (
    clean_temp_files, download_audio, transcribe_audio, 
    get_language_preference, get_video_info, extract_video_id, get_youtube_transcript
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppContext:
    """Context for the MCP server"""
    def __init__(self):
        self.model = None

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize and clean up resources"""
    # Create our context object
    context = AppContext()
    
    # Perform any initialization here
    logger.info("Initializing YouTube Transcript MCP Server...")
    
    try:
        yield context
    finally:
        # Clean up resources
        clean_temp_files()
        logger.info("Shutting down YouTube Transcript MCP Server...")

# Create an MCP server
mcp = FastMCP(
    "YouTube Transcript", 
    lifespan=app_lifespan,
    dependencies=[
        "youtube-transcript-api",
        "pytube",
        "whisper",
        "torch",
        "langdetect"
    ],
    description="An MCP server for fetching and transcribing YouTube videos"
)

@mcp.resource("youtube://{video_id}/info")
async def get_video_info_resource(video_id: str) -> str:
    """Get basic information about a YouTube video"""
    info, error = get_video_info(video_id)
    if error:
        return f"Error retrieving video information: {error}"
    
    return f"""Video Information:
Title: {info['title']}
Author: {info['author']}
Length: {info['length']} seconds
Views: {info['views']}
Published: {info['publish_date']}
Description: {info['description']}
"""

@mcp.resource("youtube://{video_id}/transcript")
async def get_transcript_resource(video_id: str) -> str:
    """Get transcript for a YouTube video as a resource"""
    logger.info(f"Resource request for transcript of video {video_id}")
    
    # Remove await since get_youtube_transcript is now sync
    transcript_text, transcript_language, _, error_msg = get_youtube_transcript(video_id)
    
    if error_msg:
        return f"""# No transcript available

Could not retrieve transcript for YouTube video: {video_id}

{error_msg}

You can try using the extract_transcript tool to generate a transcript by transcribing the audio.
"""
    
    # Add header info for resource
    header = f"# Transcript for YouTube video: {video_id}\n# Language: {transcript_language}\n\n"
    return header + transcript_text

@mcp.tool()
async def get_transcript(video_id: str, language: Optional[str] = None, ctx: Context = None) -> str:
    """
    Retrieve the transcript from a YouTube video
    
    Args:
        video_id: The YouTube video ID
        language: Preferred language for the transcript (en or vi)
        ctx: Context for progress reporting
    """
    if ctx:
        ctx.info(f"Getting transcript for video ID: {video_id}")
    
    # Remove await since get_youtube_transcript is now sync
    transcript_text, transcript_language, transcript_source, error_msg = get_youtube_transcript(
        video_id, language, ctx
    )
    
    if error_msg:
        return f"{error_msg}\n\nPlease try using the extract_transcript tool instead."
    
    # Return the successfully retrieved transcript
    transcript_info = f"Video ID: {video_id}\nLanguage: {transcript_language}\nSource: {transcript_source}\n\n"
    if ctx:
        ctx.info(f"Successfully retrieved transcript ({len(transcript_text)} characters)")
    return transcript_info + transcript_text

@mcp.tool()
async def extract_transcript(video_id: str, language: Optional[str] = None, ctx: Context = None) -> str:
    """
    Extract and transcribe audio from a YouTube video when no transcript is available
    
    Args:
        video_id: The YouTube video ID (e.g., dQw4w9WgXcQ from https://www.youtube.com/watch?v=dQw4w9WgXcQ)
        language: Preferred language for the transcript (en or vi)
    
    Returns:
        The transcribed text from the video audio
    """
    if ctx:
        ctx.info(f"Extracting transcript for video ID: {video_id}")
    
    transcript_text = None
    transcript_language = None
    whisper_lang = None
    
    try:
        # Clean old temporary files
        clean_temp_files()
        
        # If language is specified, use it for transcription
        if language:
            if language.lower() in ['en', 'english']:
                whisper_lang = 'en'
            elif language.lower() in ['vi', 'vietnamese']:
                whisper_lang = 'vi'
        
        # Download audio
        if ctx:
            ctx.info("Downloading audio...")
            await ctx.report_progress(0, 3)  # 3 steps: download, transcribe, cleanup
        
        audio_path, dl_error = download_audio(video_id)
        if dl_error:
            logger.error(f"Audio download error for video ID {video_id}: {dl_error}")
            return f"No transcript available for this video. The system could not download the audio: {dl_error}"
        
        # Transcribe with Whisper
        if audio_path:
            try:
                if ctx:
                    ctx.info("Transcribing audio... (this may take a while)")
                    await ctx.report_progress(1, 3)
                
                transcript_text, transcribe_error = transcribe_audio(audio_path, whisper_lang)
                
                # Clean up the audio file before doing any additional processing
                try:
                    if ctx:
                        ctx.info("Cleaning up temporary files...")
                        await ctx.report_progress(2, 3)
                    os.remove(audio_path)
                    logger.info(f"Removed audio file: {audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {str(e)}")
                    if ctx:
                        ctx.warning(f"Failed to clean up temporary file: {str(e)}")
                
                # Check for transcription errors
                if transcribe_error:
                    logger.error(f"Transcription error: {transcribe_error}")
                    return f"Failed to transcribe audio: {transcribe_error}"
                
                # Process successful transcription
                if transcript_text:
                    # Try to detect language if not specified
                    if not whisper_lang:
                        try:
                            transcript_language = detect(transcript_text[:100])
                        except Exception as e:
                            logger.warning(f"Language detection failed: {str(e)}")
                            transcript_language = "unknown"
                    else:
                        transcript_language = whisper_lang
                    
                    if ctx:
                        await ctx.report_progress(3, 3)
                        ctx.info(f"Transcription complete, language: {transcript_language}")
                    
                    transcript_info = f"Video ID: {video_id}\nLanguage: {transcript_language or 'auto-detected'}\nSource: whisper_extraction\n\n"
                    return transcript_info + transcript_text
                else:
                    logger.warning("Transcription completed but no text was produced")
                    return "Failed to extract transcript from the video. The transcription process completed but no text was produced."
            
            except Exception as e:
                logger.error(f"Error during transcription: {str(e)}")
                
                # Try to clean up the audio file if it exists
                try:
                    os.remove(audio_path)
                except Exception:
                    pass
                
                return f"Failed to transcribe audio due to an error: {str(e)}"
        else:
            logger.error("No audio path returned from download_audio")
            return "Failed to extract transcript from the video. No audio could be downloaded."
    
    except Exception as e:
        logger.error(f"Unexpected error in extract_transcript: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"

@mcp.tool()
async def search_youtube_video(search_query: str, ctx: Context = None) -> str:
    """
    Search for YouTube videos and return the top results
    
    Args:
        search_query: The search term or phrase to look for
    
    Returns:
        A list of top YouTube search results with video IDs
    """
    try:
        if ctx:
            ctx.info(f"Searching for YouTube videos: {search_query}")
        
        s = Search(search_query)
        results = s.results
        
        if not results:
            return "No results found for your search query."
        
        # Show top 5 results
        output = "Top YouTube search results:\n\n"
        for i, video in enumerate(results[:5], 1):
            output += f"{i}. {video.title}\n"
            output += f"   Video ID: {video.video_id}\n"
            output += f"   Channel: {video.author}\n"
            output += f"   URL: https://www.youtube.com/watch?v={video.video_id}\n\n"
        
        return output
    
    except Exception as e:
        return f"Error searching for videos: {str(e)}"

@mcp.prompt()
def transcript_youtube_video(video_url_or_id: str) -> str:
    """
    Get a transcript from a YouTube video URL or ID
    
    Args:
        video_url_or_id: The YouTube video URL or ID
    """
    # Extract video ID if a full URL is provided
    video_id = extract_video_id(video_url_or_id)
    
    return f"""Please provide a transcript for YouTube video ID {video_id}.

First, try using the get_transcript tool to fetch the available transcript.
If that fails, use the extract_transcript tool to transcribe the audio.
You may want to first look up the video information using the youtube://{video_id}/info resource.

After getting the transcript, please:
1. Summarize the main points of the video
2. Note the language of the transcript
3. Provide the full transcript
"""

@mcp.prompt()
def vietnamese_youtube_summary(video_url_or_id: str) -> str:
    """
    Get a Vietnamese summary of a YouTube video
    
    Args:
        video_url_or_id: The YouTube video URL or ID
    """
    # Extract video ID if a full URL is provided
    video_id = extract_video_id(video_url_or_id)
    
    return f"""Please get a transcript for YouTube video ID {video_id} and provide a summary in Vietnamese.

First, try using the get_transcript tool to fetch the available transcript, with language="vi" parameter.
If that fails, use the extract_transcript tool to transcribe the audio, with language="vi" parameter.
You may want to first look up the video information using the youtube://{video_id}/info resource.

After getting the transcript, please:
1. Provide a comprehensive summary in Vietnamese
2. List key points from the video in Vietnamese
3. If the original transcript wasn't in Vietnamese, note that it was translated
"""