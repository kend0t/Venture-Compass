import psycopg2
from dotenv import load_dotenv
import os
from logger import log_error  

load_dotenv()

def get_connection():
    """Establish and return a PostgreSQL connection with error logging"""
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD")
        )
    except Exception as e:
        log_error(
            error_type="DB_CONNECTION_ERROR",
            error_message=str(e),
            context={
                "function": "get_connection",
                "db_host": os.getenv("DB_HOST"),
                "db_name": os.getenv("DB_NAME"),
                "db_user": os.getenv("DB_USERNAME")
            }
        )
        raise  
