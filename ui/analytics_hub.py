import os
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, 
    QLineEdit, QComboBox, QPushButton, QHeaderView, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg

class AnalyticsHub(QWidget):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        
        # Telemetry Rolling buffers
        self.window_size = 100
        self.latency_buffer = [0.0] * self.window_size
        self.cpu_buffer = [0.0] * self.window_size
        self.ram_buffer = [0.0] * self.window_size
        self.time_steps = list(range(self.window_size))
        
        # Initialize UI Components
        self.init_ui()
        
        # Periodic database table refresh timer (2.0s)
        self.db_timer = QTimer()
        self.db_timer.timeout.connect(self.refresh_database_grid)
        self.db_timer.start(2000)
        
        # Background psutil monitor timer (1.0s)
        self.sys_timer = QTimer()
        self.sys_timer.timeout.connect(self.query_system_telemetry)
        self.sys_timer.start(1000)

    # Removed init_sql_model to use standard sqlite3 and QTableWidget

    def init_ui(self):
        # Master Layout (Horizontal split: Left=PyqtGraph, Right=QTableView Grid)
        layout = QHBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(15, 15, 15, 15)

        # Style QWidget
        self.setStyleSheet("""
            QWidget {
                background-color: #0B0F19;
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #94a3b8;
                font-size: 13px;
            }
            QLineEdit, QComboBox {
                background-color: rgba(22, 27, 38, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 6px;
                color: #f8fafc;
                min-width: 140px;
            }
            QLineEdit:focus, QComboBox:hover {
                border: 1px solid #00E5FF;
            }
            QPushButton {
                background-color: rgba(30, 41, 59, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e293b;
                border: 1px solid #00E5FF;
            }
            QPushButton#export_btn {
                background-color: #00E5FF;
                color: #0B0F19;
                border: none;
            }
            QPushButton#export_btn:hover {
                background-color: #00B4D8;
            }
            QPushButton#clear_btn {
                background-color: #FF003C;
                color: white;
                border: none;
            }
            QPushButton#clear_btn:hover {
                background-color: #CC0030;
            }
            QTableView {
                background-color: rgba(22, 27, 38, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #f8fafc;
                gridline-color: rgba(255, 255, 255, 0.04);
            }
            QHeaderView::section {
                background-color: #161B26;
                color: #f8fafc;
                padding: 6px;
                border: 1px solid rgba(255, 255, 255, 0.04);
                font-weight: bold;
            }
        """)

        # ================= LEFT: TELEMETRY PLOTS =================
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # 1. Inference Latency rolling plot
        lat_title = QLabel("SYSTEM INFERENCE LATENCY (ms)")
        lat_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00E5FF; letter-spacing: 0.5px;")
        left_layout.addWidget(lat_title)
        
        self.plot_latency = pg.PlotWidget()
        self.plot_latency.setBackground("#161B26")
        self.plot_latency.showGrid(x=True, y=True, alpha=0.1)
        self.plot_latency.setYRange(0, 100)
        self.latency_curve = self.plot_latency.plot(
            self.time_steps, self.latency_buffer, pen=pg.mkPen(color="#00E5FF", width=2)
        )
        left_layout.addWidget(self.plot_latency, 1)

        # 2. Resource Consumption rolling plot
        res_title = QLabel("NEXUS HARDWARE TELEMETRY footprint")
        res_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00E5FF; letter-spacing: 0.5px;")
        left_layout.addWidget(res_title)

        self.plot_resources = pg.PlotWidget()
        self.plot_resources.setBackground("#161B26")
        self.plot_resources.addLegend()
        self.plot_resources.showGrid(x=True, y=True, alpha=0.1)
        self.plot_resources.setYRange(0, 100)
        
        self.cpu_curve = self.plot_resources.plot(
            self.time_steps, self.cpu_buffer, name="CPU %", pen=pg.mkPen(color="#C084FC", width=2)
        )
        self.ram_curve = self.plot_resources.plot(
            self.time_steps, self.ram_buffer, name="RAM %", pen=pg.mkPen(color="#10B981", width=2)
        )
        left_layout.addWidget(self.plot_resources, 1)

        left_widget.setLayout(left_layout)
        layout.addWidget(left_widget, 1)

        # ================= RIGHT: PERSISTENT REGISTRY TABLE =================
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        reg_title = QLabel("NEXUS PERSISTENT EVENT REGISTRY")
        reg_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00E5FF; letter-spacing: 0.5px;")
        right_layout.addWidget(reg_title)

        # Filters Bar
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Category/ID...")
        self.search_input.textChanged.connect(self.filter_database_registry)
        filters_layout.addWidget(self.search_input, 1)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        from core.engine import TARGET_CLASSES
        self.category_filter.addItems(sorted(list(set(TARGET_CLASSES.values()))))
        self.category_filter.currentIndexChanged.connect(self.filter_database_registry)
        filters_layout.addWidget(self.category_filter)

        self.refresh_btn = QPushButton("Refresh Table")
        self.refresh_btn.clicked.connect(self.refresh_database_grid)
        filters_layout.addWidget(self.refresh_btn)

        right_layout.addLayout(filters_layout)

        # QTableWidget
        self.table_view = QTableWidget()
        self.table_view.setColumnCount(5)
        self.table_view.setHorizontalHeaderLabels(["ID", "Timestamp", "Category", "Tracking ID", "Confidence"])
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setSortingEnabled(True)  # Native Qt ascending/descending sorting
        self.table_view.verticalHeader().setVisible(False)
        right_layout.addWidget(self.table_view, 1)

        # Action Buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.export_btn = QPushButton("EXPORT EXCEL/CSV REPORT")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.clicked.connect(self.export_registry_to_csv)
        actions_layout.addWidget(self.export_btn, 1)

        self.clear_btn = QPushButton("WIPE REGISTRY")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.clicked.connect(self.wipe_registry_db)
        actions_layout.addWidget(self.clear_btn, 1)

        right_layout.addLayout(actions_layout)

        right_widget.setLayout(right_layout)
        layout.addWidget(right_widget, 1)

        self.setLayout(layout)

    def feed_live_latency(self, latency_ms):
        """Called by the inference thread to feed latest execution latency."""
        self.latency_buffer.pop(0)
        self.latency_buffer.append(latency_ms)
        self.latency_curve.setData(self.time_steps, self.latency_buffer)

    def query_system_telemetry(self):
        """Timer callback query to fetch psutil footprints."""
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        self.cpu_buffer.pop(0)
        self.cpu_buffer.append(cpu)
        
        self.ram_buffer.pop(0)
        self.ram_buffer.append(ram)
        
        self.cpu_curve.setData(self.time_steps, self.cpu_buffer)
        self.ram_curve.setData(self.time_steps, self.ram_buffer)

    def refresh_database_grid(self):
        """Queries the SQLite database and populates the logs table."""
        search_term = self.search_input.text().strip()
        category = self.category_filter.currentText()
        
        query = "SELECT id, timestamp, object_name, tracking_id, confidence FROM event_logs WHERE 1=1"
        params = []
        
        # 1. Category filter
        if category != "All Categories":
            query += " AND object_name = ?"
            params.append(category.lower())
            
        # 2. Text Search filter
        if search_term:
            query += " AND (object_name LIKE ? OR CAST(tracking_id AS TEXT) LIKE ?)"
            params.append(f"%{search_term}%")
            params.append(f"%{search_term}%")
            
        # Sort by timestamp descending by default when loading
        query += " ORDER BY timestamp DESC LIMIT 500"
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Disable sorting while populating to avoid issues
            self.table_view.setSortingEnabled(False)
            self.table_view.setRowCount(0)
            
            for row_idx, row in enumerate(rows):
                self.table_view.insertRow(row_idx)
                for col_idx, val in enumerate(row):
                    if col_idx == 4:  # Confidence formatting
                        val_str = f"{int(float(val) * 100)}%"
                    elif col_idx == 2:  # Category formatting (upper case)
                        val_str = str(val).upper()
                    else:
                        val_str = str(val)
                    item = QTableWidgetItem(val_str)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
                    self.table_view.setItem(row_idx, col_idx, item)
            
            # Re-enable sorting
            self.table_view.setSortingEnabled(True)
        except Exception as e:
            print(f"[AnalyticsHub] Database query failed: {e}")

    def filter_database_registry(self):
        """Callback for when search text or category changes."""
        self.refresh_database_grid()

    def export_registry_to_csv(self):
        """Exports the SQLite database registry directly into a CSV file format."""
        import csv
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
        os.makedirs(export_dir, exist_ok=True)
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Surveillance Report", 
            os.path.join(export_dir, "surveillance_registry.csv"), 
            "CSV Files (*.csv)"
        )
        
        if not filepath:
            return
            
        try:
            # Re-fetch everything directly via standard SQLite to ensure it's not filtered
            import sqlite3
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_logs ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Timestamp", "Category", "Tracking ID", "Confidence"])
                writer.writerows(rows)
                
            conn.close()
            QMessageBox.information(self, "Export Status", f"Database Registry successfully exported to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Failed to export registry: {e}")

    def wipe_registry_db(self):
        """Wipes the database table."""
        reply = QMessageBox.question(
            self, "System Wipe Confirmation",
            "WARNING: This will permanently wipe all SQLite tracking logs. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import sqlite3
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM event_logs")
                conn.commit()
                conn.close()
                self.refresh_database_grid()
                QMessageBox.information(self, "System Wipe", "Database Registry successfully cleared.")
            except Exception as e:
                QMessageBox.critical(self, "Wipe Failure", f"Failed to wipe registry: {e}")
