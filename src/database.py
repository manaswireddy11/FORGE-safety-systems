import sqlite3
import os

DB_PATH = "data/forge_safety.db"

def init_db():
    """Initializes SQLite database tables for subscriber profiles and alert logs."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Subscribers Directory Table (formerly workers)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            subscriber_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone_number TEXT UNIQUE NOT NULL,
            target_language TEXT DEFAULT 'Hindi'
        )
    """)
    
    # Alert Broadcast Log Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS broadcast_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT,
            target_language TEXT,
            script_text TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def add_subscriber(name: str, phone: str, language: str) -> bool:
    """Inserts or updates a subscriber profile in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO subscribers (full_name, phone_number, target_language) VALUES (?, ?, ?)",
            (name.strip(), phone.strip(), language)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database Error: {e}")
        return False

def get_all_subscribers():
    """Retrieves all registered subscribers."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, phone_number, target_language FROM subscribers")
    records = cursor.fetchall()
    conn.close()
    return records

# Backward-compatibility aliases so legacy calls won't crash
init_worker_db = init_db
add_worker = add_subscriber
get_all_workers = get_all_subscribers