import psycopg2
from flask import g
from config import Config
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from dotenv import load_dotenv

DATABASE_URL = Config.DATABASE_URL

load_dotenv()

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(DATABASE_URL)
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def recreate_database():
    # Connect to default postgres database
    database_url = urlsplit(DATABASE_URL)
    admin_url = urlunsplit((
        database_url.scheme,
        database_url.netloc,
        '/postgres',
        database_url.query,
        database_url.fragment,
    ))
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Drop database if exists
    database_name = os.getenv('DB_NAME', 'sports_league_db')
    cur.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    
    # Create new database
    cur.execute(f'CREATE DATABASE "{database_name}"')
    
    cur.close()
    conn.close()
    
    # Connect to new database and create schema
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Read and execute schema file
    schema_path = Path(__file__).resolve().parent / 'clean_schema.sql'
    with schema_path.open(encoding='utf-8') as f:
        cur.execute(f.read())
    
    conn.commit()
    cur.close()
    conn.close()
