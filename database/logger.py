import os
import sqlite3
import threading
import queue
import time
from datetime import datetime

class DatabaseLogger:
    def __init__(self, db_path=None):
        if db_path is None:
            # Locate db in the database folder of the workspace, or next to exe if frozen
            import sys
            if getattr(sys, 'frozen', False):
                db_dir = os.path.join(os.path.dirname(sys.executable), "database")
            else:
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
        """Initializes the database and creates all tables."""
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
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)
        
        # Create audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL
            )
        """)
        
        # Create face registry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                landmarks_blob TEXT NOT NULL,
                registered_at TEXT NOT NULL
            )
        """)
        
        # Create indexes for optimized queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON event_logs (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_object_name ON event_logs (object_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_face_name ON face_registry (name)")
        
        # Seed default admin user (username: admin, password: admin)
        import hashlib
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            admin_hash = hashlib.sha256(b"admin").hexdigest()
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", ("admin", admin_hash, "admin"))
            
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

    # ================= SECURITY & FACIAL REGISTRY HELPERS =================

    def log_audit(self, username: str, action: str):
        """Logs a security action/event to the audit table."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO audit_logs (timestamp, username, action)
                VALUES (?, ?, ?)
            """, (timestamp, username, action))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DatabaseLogger] Audit logging failed: {e}")

    def verify_user(self, username: str, password: str) -> bool:
        """Verifies if the username and password match any database record."""
        try:
            import hashlib
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            conn.close()
            if row:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                is_valid = (row[0] == password_hash)
                self.log_audit(username, "Login Attempt: SUCCESS" if is_valid else "Login Attempt: FAILURE (Wrong Password)")
                return is_valid
            self.log_audit(username, "Login Attempt: FAILURE (User Not Found)")
            return False
        except Exception as e:
            print(f"[DatabaseLogger] User verification failed: {e}")
            return False

    def register_user(self, username: str, password: str, role: str = "user") -> bool:
        """Registers a new user inside the database."""
        try:
            import hashlib
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?)
            """, (username, password_hash, role))
            conn.commit()
            conn.close()
            self.log_audit(username, f"User Registered successfully (Role: {role})")
            return True
        except Exception as e:
            print(f"[DatabaseLogger] User registration failed: {e}")
            return False

    def register_face(self, name: str, landmarks_list: list) -> bool:
        """Registers a face footprint in the database registry."""
        try:
            import json
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            landmarks_blob = json.dumps(landmarks_list)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO face_registry (name, landmarks_blob, registered_at)
                VALUES (?, ?, ?)
            """, (name, landmarks_blob, timestamp))
            conn.commit()
            conn.close()
            self.log_audit("system", f"Registered new face for: {name}")
            return True
        except Exception as e:
            print(f"[DatabaseLogger] Face registration failed: {e}")
            return False

    def get_face_registry(self) -> list:
        """Retrieves all registered face profiles."""
        try:
            import json
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            cursor.execute("SELECT name, landmarks_blob FROM face_registry")
            rows = cursor.fetchall()
            conn.close()
            
            registry = []
            for name, blob in rows:
                try:
                    registry.append({
                        "name": name,
                        "landmarks": json.loads(blob)
                    })
                except Exception:
                    pass
            return registry
        except Exception as e:
            print(f"[DatabaseLogger] Fetching face registry failed: {e}")
            return []
