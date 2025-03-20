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
from youtube_transcript_api.formatters import TextFormatter
from pytube import Search
from langdetect import detect

from app.utils import (
    clean_temp_files, download_audio, transcribe_audio, 
    get_language_preference, get_video_info, extract_video_id
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
    language = None
    transcript_text = None
    
    # Try to get transcript directly from YouTube
    try:
        # Try to get transcript in various languages
        lang_preference = get_language_preference(language)
        
        for lang in lang_preference:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                formatter = TextFormatter()
                transcript_text = formatter.format_transcript(transcript_list)
                logger.info(f"Retrieved {lang} transcript from YouTube API")
                return transcript_text
            except Exception as lang_e:
                logger.info(f"No {lang} transcript available: {str(lang_e)}")
                continue
        
        # If no specific language found, try with auto-generated
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            formatter = TextFormatter()
            transcript_text = formatter.format_transcript(transcript_list)
            logger.info("Retrieved transcript from YouTube API (auto language)")
            return transcript_text
        except Exception as e:
            logger.warning(f"Failed to get transcript from YouTube API: {str(e)}")
            
    except Exception as e:
        logger.warning(f"Failed to get transcript from YouTube API: {str(e)}")
    
    # If we reach here, no transcript was found
    return "No transcript available for this video. Use the extract_transcript tool to generate one."

@mcp.tool()
async def get_transcript(video_id: str, language: Optional[str] = None, ctx: Context = None) -> str:
    """
    Retrieve the transcript from a YouTube video
    
    Args:
        video_id: The YouTube video ID (e.g., dQw4w9WgXcQ from https://www.youtube.com/watch?v=dQw4w9WgXcQ)
        language: Preferred language for the transcript (en or vi), defaults to English then Vietnamese
    
    Returns:
        The video transcript text
    """
    if ctx:
        ctx.info(f"Getting transcript for video ID: {video_id}")
    
    transcript_text = None
    transcript_language = None
    transcript_source = "youtube_api"
    error_msg = None
    
    # Try to get transcript directly from YouTube
    try:
        # Get language preference order
        lang_preference = get_language_preference(language)
        
        # Try to get transcript in preferred languages
        for lang in lang_preference:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                formatter = TextFormatter()
                transcript_text = formatter.format_transcript(transcript_list)
                transcript_language = lang
                if ctx:
                    ctx.info(f"Retrieved {lang} transcript from YouTube API")
                break
            except Exception as lang_e:
                if ctx:
                    ctx.info(f"No {lang} transcript available: {str(lang_e)}")
                continue
        
        # If no specific language found, try with auto-generated
        if not transcript_text:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                formatter = TextFormatter()
                transcript_text = formatter.format_transcript(transcript_list)
                
                # Try to detect language
                if transcript_text:
                    try:
                        transcript_language = detect(transcript_text[:100])
                    except:
                        transcript_language = "unknown"
                
                if ctx:
                    ctx.info("Retrieved transcript from YouTube API (auto language)")
            except Exception as e:
                error_msg = str(e)
                if ctx:
                    ctx.warning(f"Failed to get transcript from YouTube API: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        if ctx:
            ctx.warning(f"Failed to get transcript from YouTube API: {error_msg}")
    
    if not transcript_text:
        return f"No transcript available for this video. Error: {error_msg or 'Unknown error'}. Try using extract_transcript tool instead."
    
    transcript_info = f"Video ID: {video_id}\nLanguage: {transcript_language}\nSource: {transcript_source}\n\n"
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
        return f"Failed to download audio: {dl_error}"
    
    # Transcribe with Whisper
    if audio_path:
        try:
            if ctx:
                ctx.info("Transcribing audio... (this may take a while)")
                await ctx.report_progress(1, 3)
            
            transcript_text, transcribe_error = transcribe_audio(audio_path, whisper_lang)
            
            # Try to detect language if not specified
            if transcript_text and not whisper_lang:
                try:
                    transcript_language = detect(transcript_text[:100])
                except:
                    transcript_language = "unknown"
            else:
                transcript_language = whisper_lang
            
            # Clean up the audio file
            if ctx:
                ctx.info("Cleaning up temporary files...")
                await ctx.report_progress(2, 3)
            
            try:
                os.remove(audio_path)
            except Exception as e:
                if ctx:
                    ctx.warning(f"Failed to clean up temporary file: {str(e)}")
            
            if ctx:
                await ctx.report_progress(3, 3)
            
            if transcribe_error:
                return f"Failed to transcribe audio: {transcribe_error}"
        except Exception as e:
            # Clean up the audio file
            try:
                os.remove(audio_path)
            except:
                pass
            
            return f"Failed to transcribe audio: {str(e)}"
    
    if not transcript_text:
        return "Failed to extract transcript from the video."
    
    transcript_info = f"Video ID: {video_id}\nLanguage: {transcript_language or 'auto-detected'}\nSource: whisper_extraction\n\n"
    return transcript_info + transcript_text

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