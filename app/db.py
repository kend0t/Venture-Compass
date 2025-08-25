import psycopg2
from dotenv import load_dotenv
import os
from logger import log_error  

load_dotenv()

def get_connection():
    """Establish and return a PostgreSQL connection with error logging"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        return psycopg2.connect(database_url)
    except Exception as e:
        log_error(
            error_type="DB_CONNECTION_ERROR",
            error_message=str(e),
            context={
                "function": "get_connection",
                "database_url_provided": bool(os.getenv("DATABASE_URL"))
            }
        )
        raise