"""
Main entry point for YouTube Transcript HTTP API server
"""
import logging
from app.flask_server import app

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting YouTube Transcript HTTP API Server...")
    app.run(debug=True, host='0.0.0.0', port=5000)