import os
import sqlite3
import pandas as pd
from datetime import datetime

class DBManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Locate db in the database folder of the workspace
            db_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(db_dir, "logs.db")
        else:
            self.db_path = db_path
        
        self.init_db()

    def init_db(self):
        """Initializes the database and creates the tables if they don't exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create detection logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detection_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                object_name TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                confidence REAL NOT NULL
            )
        """)
        
        # Create index on timestamp and object_name for faster searches
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON detection_logs (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_object_name ON detection_logs (object_name)")
        
        conn.commit()
        conn.close()

    def log_detection(self, object_name: str, track_id: int, confidence: float):
        """Inserts a single detection/tracking record into the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO detection_logs (timestamp, object_name, track_id, confidence)
            VALUES (?, ?, ?, ?)
        """, (timestamp, object_name, track_id, confidence))
        
        conn.commit()
        conn.close()

    def log_detections_batch(self, detections: list):
        """Logs a list of detections in a single transaction.
        detections should be a list of tuples: (object_name, track_id, confidence)
        """
        if not detections:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.executemany("""
            INSERT INTO detection_logs (timestamp, object_name, track_id, confidence)
            VALUES (?, ?, ?, ?)
        """, [(timestamp, obj, tid, conf) for obj, tid, conf in detections])
        
        conn.commit()
        conn.close()

    def get_logs(self, search_query: str = None, filter_class: str = None, limit: int = 1000):
        """Queries logs with optional filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT timestamp, object_name, track_id, confidence FROM detection_logs WHERE 1=1"
        params = []
        
        if filter_class and filter_class != "All":
            query += " AND object_name = ?"
            params.append(filter_class)
            
        if search_query:
            # Search by track ID or object name
            query += " AND (object_name LIKE ? OR CAST(track_id AS TEXT) LIKE ?)"
            params.append(f"%{search_query}%")
            params.append(f"%{search_query}%")
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "timestamp": row[0],
                "object_name": row[1],
                "track_id": row[2],
                "confidence": row[3]
            }
            for row in rows
        ]

    def export_to_csv(self, filepath: str) -> bool:
        """Exports the entire table to a CSV file."""
        try:
            export_dir = os.path.dirname(filepath)
            if export_dir:
                os.makedirs(export_dir, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM detection_logs ORDER BY timestamp DESC", conn)
            conn.close()
            df.to_csv(filepath, index=False)
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False

    def get_statistics(self):
        """Retrieves statistics for the analytics dashboard."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # 1. Total objects detected (all log entries)
        cursor.execute("SELECT COUNT(*) FROM detection_logs")
        stats["total_detections"] = cursor.fetchone()[0]
        
        # 2. Total unique track IDs
        cursor.execute("SELECT COUNT(DISTINCT track_id) FROM detection_logs")
        stats["total_unique_objects"] = cursor.fetchone()[0]
        
        # 3. Average confidence
        cursor.execute("SELECT AVG(confidence) FROM detection_logs")
        avg_conf = cursor.fetchone()[0]
        stats["average_confidence"] = round(avg_conf * 100, 2) if avg_conf else 0.0
        
        # 4. Class counts (unique objects tracked by class)
        cursor.execute("""
            SELECT object_name, COUNT(DISTINCT track_id) 
            FROM detection_logs 
            GROUP BY object_name
        """)
        class_counts = cursor.fetchall()
        stats["class_counts"] = {row[0]: row[1] for row in class_counts}
        
        # 5. Hourly activity (number of detections in last 24 hours)
        # SQLite datetime function is handy here
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) 
            FROM detection_logs 
            WHERE timestamp >= datetime('now', '-1 day') 
            GROUP BY hour
        """)
        hourly = cursor.fetchall()
        stats["hourly_activity"] = {row[0]: row[1] for row in hourly}
        
        conn.close()
        return stats

    def clear_logs(self):
        """Clears all records in the table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM detection_logs")
        conn.commit()
        conn.close()
