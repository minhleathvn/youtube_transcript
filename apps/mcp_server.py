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
    logger.info(f"Resource request for transcript of video {video_id}")
    
    language = None
    transcript_text = None
    transcript_language = None
    
    try:
        # Try to get transcript in various languages
        lang_preference = get_language_preference(language)
        
        # Track attempts in case all fail
        attempt_results = []
        
        for lang in lang_preference:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                transcript_text = "\n".join(line['text'] for line in transcript_list)
                
                # Check if transcript is too short or contains placeholder text
                if len(transcript_text) < 50 or "caption is updating" in transcript_text.lower():
                    logger.info(f"Retrieved {lang} transcript is too short or contains placeholder text, treating as no transcript")
                    attempt_results.append(f"{lang}: Too short or placeholder")
                    transcript_text = None
                    continue
                
                # Valid transcript found
                transcript_language = lang
                logger.info(f"Retrieved valid {lang} transcript from YouTube API")
                
                # Add header info for resource
                header = f"# Transcript for YouTube video: {video_id}\n# Language: {transcript_language}\n\n"
                return header + transcript_text
                
            except Exception as lang_e:
                error = str(lang_e)
                logger.info(f"No {lang} transcript available: {error}")
                attempt_results.append(f"{lang}: {error}")
                continue
        
        # If no specific language found, try with auto-generated
        try:
            logger.info("Attempting to fetch auto-generated transcript...")
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = "\n".join(line['text'] for line in transcript_list)
            
            # Check if transcript is too short or contains placeholder text
            if transcript_text and (len(transcript_text) < 50 or "caption is updating" in transcript_text.lower()):
                logger.info("Retrieved auto transcript is too short or contains placeholder text, treating as no transcript")
                attempt_results.append("Auto-generated: Too short or placeholder")
                transcript_text = None
            elif transcript_text:
                # Try to detect language
                try:
                    transcript_language = detect(transcript_text[:100])
                    logger.info(f"Detected language: {transcript_language}")
                except Exception as e:
                    logger.warning(f"Language detection failed: {str(e)}")
                    transcript_language = "unknown"
                
                logger.info(f"Retrieved transcript from YouTube API (auto language: {transcript_language})")
                
                # Add header info for resource
                header = f"# Transcript for YouTube video: {video_id}\n# Language: {transcript_language}\n\n"
                return header + transcript_text
                
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Failed to get auto-generated transcript: {error_msg}")
            attempt_results.append(f"Auto-generated: {error_msg}")
        
        # If all attempts failed, return a helpful message with details of attempts
        if not transcript_text:
            attempts_summary = "\n".join([f"- {attempt}" for attempt in attempt_results])
            logger.warning(f"All transcript attempts failed for video {video_id}")
            
            return f"""# No transcript available

Could not retrieve transcript for YouTube video: {video_id}

Attempted the following:
{attempts_summary}

You can try using the extract_transcript tool to generate a transcript by transcribing the audio.
"""
            
    except Exception as e:
        logger.error(f"Unexpected error in get_transcript_resource: {str(e)}")
        return f"""# Error retrieving transcript

An error occurred while retrieving the transcript for YouTube video: {video_id}

Error: {str(e)}

You can try using the extract_transcript tool instead.
"""

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
    
    try:
        # Get language preference order
        lang_preference = get_language_preference(language)
        
        if ctx:
            ctx.info(f"Language preference order: {', '.join(lang_preference)}")
        logger.info(f"Trying to get transcript for video {video_id} with language preference: {lang_preference}")
        
        # Track attempts in case all fail
        attempt_results = []
        
        # Try to get transcript in preferred languages
        for lang in lang_preference:
            try:
                logger.info(f"{video_id}: Attempting to get transcript in {lang}...")
                if ctx:
                    ctx.info(f"Attempting to fetch transcript in {lang}...")
                
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                logger.info(f"count of transcript_list: {len(transcript_list)}")
                logger.info(f"Transcript list: {transcript_list}")
                transcript_text = "\n".join(line.text for line in transcript_list)
                
                # Check if transcript is too short or contains placeholder text
                if len(transcript_text) < 50 or "caption is updating" in transcript_text.lower():
                    msg = f"Retrieved {lang} transcript is too short or contains placeholder text, treating as no transcript"
                    logger.info(msg)
                    if ctx:
                        ctx.info(msg)
                    
                    attempt_results.append(f"{lang}: Too short or placeholder")
                    transcript_text = None
                    continue
                
                logger.info(f"2222222222222222222222222222")
                # Valid transcript found
                transcript_language = lang
                msg = f"Retrieved valid {lang} transcript from YouTube API"
                logger.info(msg) 
                if ctx:
                    ctx.info(msg)
                break
                
            except Exception as lang_e:
                error = str(lang_e)
                logger.info(f"No {lang} transcript available: {error}")
                if ctx:
                    ctx.info(f"No {lang} transcript available: {error}")
                attempt_results.append(f"{lang}: {error}")
                continue
        
        # If no specific language found, try with auto-generated
        if not transcript_text:
            try:
                if ctx:
                    ctx.info("Attempting to fetch auto-generated transcript...")
                
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                transcript_text = "\n".join(line['text'] for line in transcript_list)
                
                # Check if transcript is too short or contains placeholder text
                if transcript_text and (len(transcript_text) < 50 or "caption is updating" in transcript_text.lower()):
                    msg = "Retrieved auto transcript is too short or contains placeholder text, treating as no transcript"
                    logger.info(msg)
                    if ctx:
                        ctx.info(msg)
                    
                    attempt_results.append("Auto-generated: Too short or placeholder")
                    transcript_text = None
                
                # Try to detect language if we have a valid transcript
                elif transcript_text:
                    try:
                        transcript_language = detect(transcript_text[:100])
                        logger.info(f"Detected language: {transcript_language}")
                    except Exception as e:
                        logger.warning(f"Language detection failed: {str(e)}")
                        transcript_language = "unknown"
                    
                    msg = f"Retrieved transcript from YouTube API (auto language: {transcript_language})"
                    logger.info(msg)
                    if ctx:
                        ctx.info(msg)
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to get auto-generated transcript: {error_msg}")
                if ctx:
                    ctx.warning(f"Failed to get auto-generated transcript: {error_msg}")
                attempt_results.append(f"Auto-generated: {error_msg}")
        
        # If all attempts failed, return a helpful message with details of attempts
        if not transcript_text:
            attempts_summary = "\n".join([f"- {attempt}" for attempt in attempt_results])
            logger.warning(f"All transcript attempts failed for video {video_id}")
            
            error_details = f"No transcript available for this video. Attempted the following:\n{attempts_summary}\n\nPlease try using the extract_transcript tool instead."
            if ctx:
                ctx.warning(error_details)
            return error_details
        
        # Return the successfully retrieved transcript
        transcript_info = f"Video ID: {video_id}\nLanguage: {transcript_language}\nSource: {transcript_source}\n\n"
        if ctx:
            ctx.info(f"Successfully retrieved transcript ({len(transcript_text)} characters)")
        return transcript_info + transcript_text
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error in get_transcript: {error_msg}")
        if ctx:
            ctx.error(f"Unexpected error: {error_msg}")
        return f"An unexpected error occurred while retrieving the transcript: {error_msg}. Try using extract_transcript tool instead."

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