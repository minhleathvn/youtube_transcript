"""
Flask server for YouTube transcript API
"""
import logging
from flask import Flask, request, jsonify

from youtube_transcript_api import YouTubeTranscriptApi
from langdetect import detect

from apps.utils import (
    clean_temp_files, download_audio, transcribe_audio, 
    get_language_preference, get_video_info
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/transcript', methods=['GET'])
def get_transcript():
    """API endpoint to get transcript for a YouTube video"""
    video_id = request.args.get('video_id')
    language = request.args.get('language')  # Optional language preference
    force_extract = request.args.get('force_extract', 'false').lower() == 'true'
    
    if not video_id:
        return jsonify({"error": "Missing video_id parameter"}), 400
    
    # Clean old temporary files
    clean_temp_files()
    
    transcript_text = None
    transcript_language = None
    transcript_source = "youtube_api"
    error_msg = None
    
    # Try to get transcript directly from YouTube if not forcing extraction
    if not force_extract:
        try:
            # Get language preference order
            lang_preference = get_language_preference(language)
            
            # Try to get transcript in preferred languages
            for lang in lang_preference:
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                    transcript_text = "\n".join(line['text'] for line in transcript_list)
                    
                    # Check if transcript is too short or contains placeholder text
                    if len(transcript_text) < 50 or "caption is updating" in transcript_text.lower():
                        logger.info(f"Retrieved {lang} transcript is too short or contains placeholder text, treating as no transcript")
                        transcript_text = None
                        continue
                        
                    transcript_language = lang
                    logger.info(f"Retrieved {lang} transcript from YouTube API")
                    break
                except Exception as lang_e:
                    logger.info(f"No {lang} transcript available: {str(lang_e)}")
                    continue
            
            # If no specific language found, try with auto-generated
            if not transcript_text:
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                    transcript_text = "\n".join(line['text'] for line in transcript_list)
                    
                    # Check if transcript is too short or contains placeholder text
                    if transcript_text and (len(transcript_text) < 50 or "caption is updating" in transcript_text.lower()):
                        logger.info("Retrieved auto transcript is too short or contains placeholder text, treating as no transcript")
                        transcript_text = None
                    # Try to detect language
                    elif transcript_text:
                        try:
                            transcript_language = detect(transcript_text[:100])
                        except:
                            transcript_language = "unknown"
                        logger.info("Retrieved transcript from YouTube API (auto language)")
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Failed to get transcript from YouTube API: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Failed to get transcript from YouTube API: {error_msg}")
    
    # If transcript not found or forcing extraction, try manual extraction
    if not transcript_text or force_extract:
        logger.info("Attempting manual audio extraction and transcription")
        transcript_source = "whisper_extraction"
        
        # Download audio - changed from async to sync
        audio_path, dl_error = download_audio(video_id)
        if dl_error:
            logger.error(f"Audio download error: {dl_error}")
            error_detail = f"{error_msg}. Audio download error: {dl_error}" if error_msg else f"Audio download error: {dl_error}"
            return jsonify({
                "error": f"Failed to get transcript: {error_detail}",
                "video_id": video_id,
                "transcript": "No transcript available for this video.",
                "status": "error"
            }), 404  # Use 404 to indicate the resource (transcript) couldn't be found
        
        # Transcribe with Whisper
        if audio_path:
            try:
                # If language is specified, use it for transcription
                whisper_lang = None
                if language:
                    if language.lower() in ['en', 'english']:
                        whisper_lang = 'en'
                    elif language.lower() in ['vi', 'vietnamese']:
                        whisper_lang = 'vi'
                
                # Changed from async to sync
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
                try:
                    import os
                    os.remove(audio_path)
                except:
                    pass
                
                if transcribe_error:
                    return jsonify({
                        "error": f"Failed to get transcript: {error_msg}. Transcription error: {transcribe_error}"
                    }), 500
            except Exception as e:
                # Clean up the audio file
                try:
                    import os
                    os.remove(audio_path)
                except:
                    pass
                
                return jsonify({
                    "error": f"Failed to transcribe audio: {str(e)}"
                }), 500
    
    if not transcript_text:
        logger.error(f"No transcript available for video ID: {video_id}. Error: {error_msg or 'Unknown error'}")
        return jsonify({
            "error": f"Failed to get transcript: {error_msg or 'Unknown error'}",
            "video_id": video_id,
            "transcript": "No transcript available for this video.",
            "status": "error"
        }), 404  # Use 404 to indicate the resource (transcript) couldn't be found
    
    return jsonify({
        "video_id": video_id,
        "transcript": transcript_text,
        "language": transcript_language,
        "source": transcript_source
    })

@app.route('/video/info', methods=['GET'])
def video_info():
    """Get information about a YouTube video"""
    video_id = request.args.get('video_id')
    
    if not video_id:
        return jsonify({"error": "Missing video_id parameter"}), 400
    
    info, error = get_video_info(video_id)
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify(info)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200