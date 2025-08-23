import logging
from datetime import datetime
import traceback

def setup_error_logging():
    """Setup error logging to logs.txt file"""
    logger = logging.getLogger('chatbot_errors')
    logger.setLevel(logging.ERROR)

    file_handler = logging.FileHandler('logs.txt', mode='a', encoding='utf-8')
    file_handler.setLevel(logging.ERROR)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)

    return logger

error_logger = setup_error_logging()

def log_error(error_type, error_message, context=None, thread_id=None):
    """Log errors to logs.txt with context information"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": str(error_message),
            "thread_id": thread_id,
            "context": context,
            "traceback": traceback.format_exc()
        }

        error_logger.error(f"CHATBOT_ERROR: {log_entry}")
        print(f"ERROR LOGGED: {error_type} - {error_message}")  # Dev console
    except Exception as logging_error:
        print(f"Failed to log error: {logging_error}")
