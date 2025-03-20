"""
Shared utilities for YouTube transcript extraction
"""
import os
import tempfile
import logging
import time
from typing import Optional, Tuple, List

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from pytube import YouTube
# Use the correct whisper import for OpenAI's speech recognition model
import whisper
from langdetect import detect

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create temporary directory for downloads
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'youtube_transcripts')
os.makedirs(TEMP_DIR, exist_ok=True)

# Initialize whisper model (load on startup)
MODEL = None  # We'll load it lazily on first use

def get_whisper_model():
    """Get or initialize the Whisper model"""
    global MODEL
    if MODEL is None:
        logger.info("Loading Whisper model...")
        MODEL = whisper.load_model("base")
    return MODEL

def clean_temp_files():
    """Clean temporary files older than 1 hour"""
    current_time = time.time()
    for filename in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, filename)
        # If file is older than 1 hour, remove it
        if os.path.isfile(file_path) and os.stat(file_path).st_mtime < current_time - 3600:
            try:
                os.remove(file_path)
                logger.info(f"Removed old temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Error removing temporary file {file_path}: {str(e)}")

def download_audio(video_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Download audio from YouTube video"""
    try:
        # Try to download using pytube
        url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"Attempting to download audio from: {url}")
        
        # Make multiple attempts with different configurations
        for attempt in range(3):
            try:
                logger.info(f"Download attempt {attempt+1}...")
                if attempt == 0:
                    yt = YouTube(url)
                elif attempt == 1:
                    # Try with different options
                    yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
                else:
                    # Try another approach
                    yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
                
                # Try to get streams
                audio_stream = yt.streams.filter(only_audio=True).first()
                if not audio_stream:
                    logger.warning("No audio stream available for this video")
                    continue
                
                # Download to temp directory
                output_path = os.path.join(TEMP_DIR, f"{video_id}.mp4")
                audio_stream.download(output_path=TEMP_DIR, filename=f"{video_id}.mp4")
                
                # Check if file was actually downloaded
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"Successfully downloaded audio to: {output_path}")
                    return output_path, None
                else:
                    logger.warning(f"Download appeared to succeed but file is missing or empty: {output_path}")
                    
            except Exception as e:
                logger.warning(f"Download attempt {attempt+1} failed: {str(e)}")
        
        # If all attempts failed, return error
        error_msg = "Failed to download audio after multiple attempts. The video may be restricted, private, or age-limited."
        logger.error(error_msg)
        return None, error_msg
            
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        return None, str(e)

def transcribe_audio(audio_path: str, language: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Transcribe audio using Whisper"""
    try:
        model = get_whisper_model()
        
        # Use specific language if provided, otherwise auto-detect
        if language:
            result = model.transcribe(audio_path, language=language)
        else:
            result = model.transcribe(audio_path)
        
        return result["text"], None
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return None, str(e)

def get_language_preference(requested_lang: Optional[str] = None) -> List[str]:
    """Determine language preference order"""
    if requested_lang:
        if requested_lang.lower() in ['en', 'english']:
            return ['en', 'vi']
        elif requested_lang.lower() in ['vi', 'vietnamese']:
            return ['vi', 'en']
    
    # Default preference order
    return ['en', 'vi']

def get_video_info(video_id: str) -> dict:
    """Get basic information about a YouTube video"""
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        info = {
            "title": yt.title,
            "author": yt.author,
            "length": yt.length,
            "views": yt.views,
            "publish_date": str(yt.publish_date) if yt.publish_date else None,
            "description": yt.description
        }
        return info, None
    except Exception as e:
        logger.error(f"Error retrieving video information: {str(e)}")
        return None, str(e)

def extract_video_id(video_url_or_id: str) -> str:
    """Extract video ID from URL or return as-is if already an ID"""
    video_id = video_url_or_id
    if "youtube.com" in video_url_or_id or "youtu.be" in video_url_or_id:
        if "youtube.com/watch?v=" in video_url_or_id:
            video_id = video_url_or_id.split("youtube.com/watch?v=")[1].split("&")[0]
        elif "youtu.be/" in video_url_or_id:
            video_id = video_url_or_id.split("youtu.be/")[1].split("?")[0]
    return video_id