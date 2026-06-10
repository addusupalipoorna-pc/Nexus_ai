import os
import sqlite3
import threading
import queue
import time
from datetime import datetime

class DatabaseLogger:
    def __init__(self, db_path=None):
        if db_path is None:
            # Locate db in the database folder of the workspace
            db_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(db_dir, "nexus_events.db")
        else:
            self.db_path = db_path
            
        self.log_queue = queue.Queue()
        self.is_running = True
        
        self.init_db()
        
        # Start background worker thread for asynchronous writes
        self.worker_thread = threading.Thread(target=self._db_worker, daemon=True)
        self.worker_thread.start()

    def init_db(self):
        """Initializes the database and creates the event logs table."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create event logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                object_name TEXT NOT NULL,
                tracking_id INTEGER NOT NULL,
                confidence REAL NOT NULL
            )
        """)
        
        # Create indexes for optimized queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON event_logs (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_object_name ON event_logs (object_name)")
        
        conn.commit()
        conn.close()

    def log_event(self, object_name: str, tracking_id: int, confidence: float):
        """Pushes a log event to the queue to be written asynchronously."""
        if self.is_running:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_queue.put((timestamp, object_name, tracking_id, confidence))

    def _db_worker(self):
        """Background worker thread that processes batch database writes."""
        print("[logger] Background thread started.")
        try:
            print(f"[logger] Connecting to SQLite DB at: {self.db_path}")
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            print("[logger] SQLite connected successfully.")
            cursor = conn.cursor()
        except Exception as e:
            print(f"[logger] SQLite connection failed: {e}")
            return
        
        last_commit_time = time.time()
        print("[logger] Entering worker loop.")
        
        while self.is_running or not self.log_queue.empty():
            try:
                # Accumulate a batch of logs
                batch = []
                # Fetch first item (blocks up to 0.5s if queue is empty)
                try:
                    item = self.log_queue.get(timeout=0.5)
                    batch.append(item)
                    self.log_queue.task_done()
                    
                    # Pull any remaining items currently in queue
                    while len(batch) < 100:  # Cap batch size at 100
                        try:
                            item = self.log_queue.get_nowait()
                            batch.append(item)
                            self.log_queue.task_done()
                        except queue.Empty:
                            break
                except queue.Empty:
                    pass
                
                # Write batch to DB
                if batch:
                    cursor.executemany("""
                        INSERT INTO event_logs (timestamp, object_name, tracking_id, confidence)
                        VALUES (?, ?, ?, ?)
                    """, batch)
                    conn.commit()
                    last_commit_time = time.time()
                        
            except Exception as e:
                print(f"[DatabaseLogger] Worker Exception: {e}")
                
        # Final commit and close
        try:
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_db_path(self):
        return self.db_path

    def close(self):
        """Stops the worker thread and commits any remaining logs."""
        self.is_running = False
        self.worker_thread.join(timeout=3.0)
