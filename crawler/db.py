""" Database helpers (sqlite3) 
Provides init_db, claim_next_url, add_url_if_new, mark_done, mark_failed """ 
import sqlite3 
from datetime import datetime

DB_FILE = "crawler.db"

def init_db(db_file=DB_FILE): 
    conn = sqlite3.connect(db_file, check_same_thread=False) 
    cur = conn.cursor() 
    cur.execute(""" 
                CREATE TABLE IF NOT EXISTS frontier ( 
                id INTEGER PRIMARY KEY, 
                url TEXT UNIQUE, 
                status TEXT, 
                added_at TIMESTAMP, 
                last_try TIMESTAMP, 
                depth INTEGER DEFAULT 0, 
                retries INTEGER DEFAULT 0 
                )
                 """) 
    cur.execute(""" 
                CREATE TABLE IF NOT EXISTS visited ( 
                url TEXT PRIMARY KEY, 
                fetched_at TIMESTAMP, 
                status_code INTEGER 
                ) 
                """) 
    conn.commit() 
    return conn

# Claim next url atomically. Returns dict or None

def claim_next_url(conn): 
    cur = conn.cursor() 
    # reset stuck in_progress older than 1 hour 
    cur.execute("UPDATE frontier SET status='pending' WHERE status='in_progress' AND last_try < datetime('now','-1 hour')") 
    conn.commit() 
    try: 
        cur.execute("BEGIN IMMEDIATE") 
        cur.execute("SELECT id, url, depth, retries FROM frontier WHERE status='pending' ORDER BY added_at LIMIT 1") 
        row = cur.fetchone() 
        if not row: 
            conn.commit() 
            return None 
        row_id, url, depth, retries = row 
        now = datetime.utcnow().isoformat() 
        cur.execute("UPDATE frontier SET status='in_progress', last_try=?, retries=? WHERE id=? AND status='pending'", (now, retries+1, row_id)) 
        if cur.rowcount == 0: 
            conn.commit() 
            return None 
        conn.commit() 
        return {"id": row_id, "url": url, "depth": depth, "retries": retries+1} 
    except sqlite3.OperationalError: 
        conn.rollback() 
        return None

def add_url_if_new(conn, url, depth=0): 
    try: 
        cur = conn.cursor() 
        cur.execute("INSERT OR IGNORE INTO frontier (url, status, added_at, depth) VALUES (?, 'pending', datetime('now'), ?)", (url, depth)) 
        conn.commit() 
    except Exception: 
        conn.rollback()

def mark_done(conn, url, status_code): 
    cur = conn.cursor() 
    cur.execute("INSERT OR REPLACE INTO visited (url, fetched_at, status_code) VALUES (?, datetime('now'), ?)", (url, status_code)) 
    cur.execute("UPDATE frontier SET status='done' WHERE url=?", (url,)) 
    conn.commit()

def mark_failed(conn, url): 
    cur = conn.cursor() 
    cur.execute("UPDATE frontier SET status='failed' WHERE url=?", (url,)) 
    conn.commit()
