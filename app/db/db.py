# db.py
import sqlite3
from app.config import DB_PATH

def init_db(db_path=DB_PATH/'keywords.db'):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS features (
        id INTEGER PRIMARY KEY,
        feature_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY,
        keyword TEXT NOT NULL,
        feature_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (feature_id) REFERENCES features(id)
    );

    CREATE TABLE IF NOT EXISTS expanded_keywords (
        id INTEGER PRIMARY KEY,
        keyword_id INTEGER NOT NULL,
        expanded_keywords TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(keyword_id),
        FOREIGN KEY (keyword_id) REFERENCES keywords(id)
    );
    """)

    conn.commit()
    return conn

