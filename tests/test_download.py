import os
import logging
import tempfile
from apps.utils import download_audio, transcribe_audio, get_whisper_model

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_download_and_transcribe(video_id):
    """Test downloading and transcribing a YouTube video"""
    logger.info(f"Testing download and transcription for video ID: {video_id}")
    
    # Make sure the model is loaded
    logger.info("Loading Whisper model...")
    model = get_whisper_model()
    logger.info("Whisper model loaded")
    
    # Create a test directory for downloads
    temp_dir = tempfile.mkdtemp(prefix="youtube_test_")
    logger.info(f"Created temporary directory: {temp_dir}")
    
    try:
        # Step 1: Try the direct download approach from utils.py
        logger.info("Attempting download using the app's download_audio function...")
        audio_path, dl_error = download_audio(video_id)
        
        if dl_error:
            logger.error(f"Download failed with error: {dl_error}")
        else:
            logger.info(f"Download succeeded, file saved at: {audio_path}")
            
            # Step 2: Try to transcribe the downloaded audio
            logger.info("Attempting to transcribe the audio...")
            transcript_text, transcribe_error = transcribe_audio(audio_path, None)
            
            if transcribe_error:
                logger.error(f"Transcription failed with error: {transcribe_error}")
            else:
                logger.info(f"Transcription succeeded, length: {len(transcript_text)}")
                logger.info(f"Transcript preview: {transcript_text[:200]}...")
                
            # Clean up the audio file
            try:
                os.remove(audio_path)
                logger.info(f"Cleaned up audio file: {audio_path}")
            except Exception as e:
                logger.error(f"Failed to clean up audio file: {str(e)}")
        
        # Step 3: Try alternative download approach using pytube directly
        try:
            from pytube import YouTube
            
            logger.info("Attempting direct download using pytube...")
            yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
            
            logger.info(f"Video title: {yt.title}")
            logger.info(f"Author: {yt.author}")
            logger.info(f"Length: {yt.length} seconds")
            logger.info(f"Views: {yt.views}")
            
            # Get available streams
            logger.info("Listing available streams:")
            streams = yt.streams
            for i, stream in enumerate(streams[:5]):  # Show first 5 streams
                logger.info(f"Stream {i}: {stream}")
            
            # Try to get an audio stream
            audio_stream = yt.streams.filter(only_audio=True).first()
            if audio_stream:
                # Download to temp directory
                output_path = os.path.join(temp_dir, f"{video_id}_direct.mp4")
                logger.info(f"Downloading audio stream to {output_path}...")
                audio_stream.download(output_path=temp_dir, filename=f"{video_id}_direct.mp4")
                
                logger.info(f"Direct download succeeded, file saved at: {output_path}")
                
                # Try to transcribe
                logger.info("Attempting to transcribe the directly downloaded audio...")
                transcript_text, transcribe_error = transcribe_audio(output_path, None)
                
                if transcribe_error:
                    logger.error(f"Direct transcription failed with error: {transcribe_error}")
                else:
                    logger.info(f"Direct transcription succeeded, length: {len(transcript_text)}")
                    logger.info(f"Direct transcript preview: {transcript_text[:200]}...")
                
                # Clean up
                try:
                    os.remove(output_path)
                    logger.info(f"Cleaned up direct audio file: {output_path}")
                except Exception as e:
                    logger.error(f"Failed to clean up direct audio file: {str(e)}")
            else:
                logger.error("No audio stream available for direct download")
                
        except Exception as e:
            logger.error(f"Direct download failed with error: {str(e)}")
    
    finally:
        # Clean up the temporary directory
        try:
            os.rmdir(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Failed to clean up temporary directory: {str(e)}")

if __name__ == "__main__":
    import asyncio
    
    # Test with the video ID kx6N9XbOLXw
    video_id = "kx6N9XbOLXw"
    
    # Run the test
    asyncio.run(test_download_and_transcribe(video_id))