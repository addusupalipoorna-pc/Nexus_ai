import os
import sqlite3
import pandas as pd
from datetime import datetime

class Reporter:
    @staticmethod
    def export_events_to_csv(db_path: str, output_path: str) -> bool:
        """Queries SQLite and exports event logs to CSV."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            query = """
                SELECT timestamp, object_name as object_label, tracking_id, confidence 
                FROM event_logs 
                ORDER BY timestamp DESC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            df.to_csv(output_path, index=False)
            return True
        except Exception as e:
            print(f"[Reporter] CSV Export Failed: {e}")
            return False

    @staticmethod
    def export_events_to_html(db_path: str, output_path: str) -> bool:
        """Generates a premium glassmorphism styled HTML executive report from the SQLite database."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Fetch summary statistics
            cursor.execute("SELECT COUNT(*) FROM event_logs")
            total_detections = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT tracking_id) FROM event_logs")
            total_unique_tracks = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(confidence) FROM event_logs")
            avg_conf = cursor.fetchone()[0]
            avg_conf_pct = f"{round(avg_conf * 100, 1)}%" if avg_conf else "0.0%"
            
            # Fetch last 100 logs
            cursor.execute("""
                SELECT timestamp, object_name, tracking_id, confidence 
                FROM event_logs 
                ORDER BY timestamp DESC 
                LIMIT 100
            """)
            logs = cursor.fetchall()
            conn.close()
            
            # Construct styled HTML string
            report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_rows_html = ""
            for ts, label, tid, conf in logs:
                log_rows_html += f"""
                <tr>
                    <td>{ts}</td>
                    <td class="badge">{label.upper()}</td>
                    <td>{tid}</td>
                    <td>{round(conf * 100, 1)}%</td>
                </tr>
                """
                
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NEXUS AI // EXECUTIVE SECURITY REPORT</title>
    <style>
        body {{
            background-color: #0B0F19;
            color: #E2E8F0;
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 40px;
        }}
        .header {{
            border-bottom: 2px solid #00E5FF;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #00E5FF;
            margin: 0;
            letter-spacing: 2px;
            font-size: 28px;
        }}
        .header p {{
            color: #64748B;
            margin: 5px 0 0 0;
            font-size: 12px;
            font-weight: bold;
        }}
        .stats-container {{
            display: flex;
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            flex: 1;
            background-color: rgba(22, 27, 38, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #00E5FF;
            margin-bottom: 5px;
        }}
        .card .title {{
            font-size: 11px;
            color: #64748B;
            font-weight: bold;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: rgba(22, 27, 38, 0.4);
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        th {{
            background-color: rgba(14, 19, 31, 0.8);
            color: #94A3B8;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        tr:hover td {{
            background-color: rgba(255, 255, 255, 0.02);
        }}
        td {{
            color: #CBD5E1;
            font-size: 13px;
        }}
        .badge {{
            color: #00E5FF;
            font-weight: bold;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NEXUS AI // EXECUTIVE REPORT</h1>
        <p>GENERATED AT: {report_time} // CLASSIFICATION: SECURE</p>
    </div>
    
    <div class="stats-container">
        <div class="card">
            <div class="value">{total_detections}</div>
            <div class="title">Total System Detections</div>
        </div>
        <div class="card">
            <div class="value">{total_unique_tracks}</div>
            <div class="title">Unique Tracked Objects</div>
        </div>
        <div class="card">
            <div class="value">{avg_conf_pct}</div>
            <div class="title">Average Confidence</div>
        </div>
    </div>
    
    <h2>EVENT AUDIT LOGS (LATEST 100 RECORDS)</h2>
    <table>
        <thead>
            <tr>
                <th>Timestamp</th>
                <th>Tracked Class Name</th>
                <th>Tracking BBox ID</th>
                <th>Confidence Score</th>
            </tr>
        </thead>
        <tbody>
            {log_rows_html}
        </tbody>
    </table>
</body>
</html>
"""
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return True
        except Exception as e:
            print(f"[Reporter] HTML Export Failed: {e}")
            return False
