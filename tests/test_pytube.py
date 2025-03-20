import os
import logging
import tempfile
from pytube import YouTube
from pytube.exceptions import PytubeError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pytube_download(video_id):
    """Test downloading a YouTube video using pytube directly"""
    logger.info(f"Testing download for video ID: {video_id}")
    
    # Create a test directory for downloads
    temp_dir = tempfile.mkdtemp(prefix="youtube_test_")
    logger.info(f"Created temporary directory: {temp_dir}")
    
    try:
        # Try to get video info
        url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"Getting info for URL: {url}")
        
        # Create YouTube object with more options and retry mechanism
        for attempt in range(3):
            try:
                logger.info(f"Attempt {attempt+1} to fetch video info...")
                # Try with different configurations
                if attempt == 0:
                    yt = YouTube(url)
                elif attempt == 1:
                    # Try with different options
                    yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
                else:
                    # Try with different headers
                    yt = YouTube(
                        url,
                        use_oauth=False,
                        allow_oauth_cache=False
                    )
                
                # Try to get video details
                logger.info(f"Video title: {yt.title}")
                logger.info(f"Author: {yt.author}")
                logger.info(f"Length: {yt.length} seconds")
                logger.info(f"Video ID: {yt.video_id}")
                
                # Get stream info
                logger.info("Getting stream information...")
                streams = yt.streams.filter()
                logger.info(f"Total streams: {len(streams)}")
                
                # Show some stream details
                for i, stream in enumerate(streams[:5]):
                    logger.info(f"Stream {i}: {stream}")
                
                # Try to find audio streams
                audio_streams = yt.streams.filter(only_audio=True)
                logger.info(f"Audio streams: {len(audio_streams)}")
                
                if audio_streams:
                    # Get the first audio stream
                    audio_stream = audio_streams.first()
                    logger.info(f"Selected audio stream: {audio_stream}")
                    
                    # Try to download
                    output_path = os.path.join(temp_dir, f"{video_id}.mp4")
                    logger.info(f"Downloading to: {output_path}")
                    
                    # Download the stream
                    audio_stream.download(output_path=temp_dir, filename=f"{video_id}.mp4")
                    
                    # Check if file was downloaded successfully
                    if os.path.exists(output_path):
                        file_size = os.path.getsize(output_path)
                        logger.info(f"Download successful! File size: {file_size} bytes")
                        
                        # Clean up
                        os.remove(output_path)
                        logger.info(f"Removed test file: {output_path}")
                    else:
                        logger.error(f"File does not exist after download: {output_path}")
                else:
                    logger.error("No audio streams found for this video")
                
                # If we got here, we succeeded
                break
                
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed with error: {str(e)}")
                if attempt == 2:
                    logger.error("All attempts to download failed")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    
    finally:
        # Clean up the temporary directory
        try:
            os.rmdir(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Failed to clean up temporary directory: {str(e)}")

if __name__ == "__main__":
    # Test with the video ID kx6N9XbOLXw
    video_id = "kx6N9XbOLXw"
    
    # Run the test
    test_pytube_download(video_id)
    
    # Try an alternative known working video as a comparison
    logger.info("\n\nTrying with a different video for comparison:")
    test_pytube_download("dQw4w9WgXcQ")  # Rick Astley - Never Gonna Give You Up