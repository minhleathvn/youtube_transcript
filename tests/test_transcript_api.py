import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_transcript_api(video_id):
    """Test fetching transcripts directly from the YouTube Transcript API"""
    logger.info(f"Testing transcript API for video ID: {video_id}")
    
    try:
        # Try to get a transcript in any language
        logger.info("Attempting to fetch transcript in any language...")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)
        
        logger.info(f"Transcript length: {len(transcript_text)}")
        logger.info(f"Transcript snippet: {transcript_text[:100]}...")
        
        if "caption is updating" in transcript_text.lower():
            logger.warning("Transcript contains 'caption is updating' placeholder text")
        
        if len(transcript_text) < 50:
            logger.warning("Transcript is very short (less than 50 characters)")
        
        return transcript_text
    
    except Exception as e:
        logger.error(f"Error fetching transcript: {str(e)}")
        
        # Try to get available transcripts
        try:
            logger.info("Checking available transcript languages...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            logger.info("Available transcripts:")
            for transcript in transcript_list:
                logger.info(f"  - {transcript.language_code} ({transcript.language}): {transcript.is_generated}")
                
        except Exception as list_e:
            logger.error(f"Error listing available transcripts: {str(list_e)}")
        
        return None

if __name__ == "__main__":
    # Test with the video ID kx6N9XbOLXw
    video_id = "kx6N9XbOLXw"
    
    # Run the test
    test_transcript_api(video_id)
    
    # Try an alternative known working video as a comparison
    logger.info("\n\nTrying with a different video for comparison:")
    test_transcript_api("dQw4w9WgXcQ")  # Rick Astley - Never Gonna Give You Up