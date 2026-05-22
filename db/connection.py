import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

load_dotenv()

def get_connection_params(): #This is the default values in case the .env doesn't have any
    return{
        "host":os.getenv("DB_HOST","localhost"),
        "port":os.getenv("DB_PORT","5432"),
        "dbname":os.getenv("DB_NAME","DevSecOps_Analytics"),
        "user":os.getenv("DB_User","postgres"),
        "password":os.getenv("DB_password","postgres"),
    }

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**get_connection_params())
    register_vector(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
        
@contextmanager
def get_db_cursor():
    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()