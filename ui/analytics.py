import os
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QLineEdit, QComboBox, QPushButton, QHeaderView,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
from database.db_manager import DBManager

class AnalyticsPanel(QWidget):
    def __init__(self, db_manager: DBManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        
        # Performance buffers for rolling charts
        self.max_points = 50
        self.cpu_data = [0.0] * self.max_points
        self.mem_data = [0.0] * self.max_points
        self.fps_data = [0.0] * self.max_points
        self.time_indices = list(range(self.max_points))
        
        # Object count buffers
        self.count_history = {
            "person": [0.0] * self.max_points,
            "vehicle": [0.0] * self.max_points,
            "other": [0.0] * self.max_points
        }
        
        self.init_ui()
        
        # Timers
        self.perf_timer = QTimer()
        self.perf_timer.timeout.connect(self.update_perf_chart)
        self.perf_timer.start(1000)  # Update performance every 1 second
        
        self.db_refresh_timer = QTimer()
        self.db_refresh_timer.timeout.connect(self.refresh_log_table)
        self.db_refresh_timer.start(3000)  # Refresh log table every 3 seconds

    def init_ui(self):
        # Main layout: Split into Left (Charts) and Right (Logs table)
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #94a3b8;
                font-size: 13px;
            }
            QLineEdit, QComboBox {
                background-color: #1e293b;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 6px;
                color: #f8fafc;
                min-width: 120px;
            }
            QLineEdit:focus, QComboBox:hover {
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background-color: #334155;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #475569;
            }
            QPushButton#export_btn {
                background-color: #0ea5e9;
            }
            QPushButton#export_btn:hover {
                background-color: #0284c7;
            }
            QPushButton#clear_btn {
                background-color: #ef4444;
            }
            QPushButton#clear_btn:hover {
                background-color: #dc2626;
            }
            QTableWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                gridline-color: #334155;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0ea5e9;
                color: white;
            }
            QHeaderView::section {
                background-color: #334155;
                color: #f8fafc;
                padding: 6px;
                border: 1px solid #1e293b;
                font-weight: bold;
            }
        """)

        # ================= LEFT COLUMN: CHARTS =================
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # 1. Performance Monitor Chart
        perf_title = QLabel("SYSTEM PERFORMANCE MONITOR")
        perf_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8; letter-spacing: 0.5px;")
        left_layout.addWidget(perf_title)
        
        # PyQtGraph widget configuration
        self.perf_plot = pg.PlotWidget()
        self.perf_plot.setBackground("#1e293b")
        self.perf_plot.addLegend()
        self.perf_plot.showGrid(x=True, y=True, alpha=0.15)
        self.perf_plot.setYRange(0, 100)
        
        # Plot curves
        self.cpu_curve = self.perf_plot.plot(
            self.time_indices, self.cpu_data, name="CPU %", pen=pg.mkPen(color="#0ea5e9", width=2)
        )
        self.mem_curve = self.perf_plot.plot(
            self.time_indices, self.mem_data, name="Memory %", pen=pg.mkPen(color="#10b981", width=2)
        )
        self.fps_curve = self.perf_plot.plot(
            self.time_indices, self.fps_data, name="Inference FPS", pen=pg.mkPen(color="#f43f5e", width=2)
        )
        
        left_layout.addWidget(self.perf_plot, 1)

        # 2. Object Activity Chart
        obj_title = QLabel("LIVE OBJECT TELEMETRY")
        obj_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8; letter-spacing: 0.5px;")
        left_layout.addWidget(obj_title)

        self.obj_plot = pg.PlotWidget()
        self.obj_plot.setBackground("#1e293b")
        self.obj_plot.addLegend()
        self.obj_plot.showGrid(x=True, y=True, alpha=0.15)
        
        self.person_curve = self.obj_plot.plot(
            self.time_indices, self.count_history["person"], name="Persons", pen=pg.mkPen(color="#ef4444", width=2)
        )
        self.vehicle_curve = self.obj_plot.plot(
            self.time_indices, self.count_history["vehicle"], name="Vehicles", pen=pg.mkPen(color="#10b981", width=2)
        )
        self.other_curve = self.obj_plot.plot(
            self.time_indices, self.count_history["other"], name="Others", pen=pg.mkPen(color="#eab308", width=2)
        )

        left_layout.addWidget(self.obj_plot, 1)

        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget, 1)

        # ================= RIGHT COLUMN: DATABASE LOGS =================
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        log_title = QLabel("HISTORICAL DETECTION LOGS")
        log_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8; letter-spacing: 0.5px;")
        right_layout.addWidget(log_title)

        # Filter panel
        filter_panel = QHBoxLayout()
        filter_panel.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Label/ID...")
        self.search_input.textChanged.connect(self.refresh_log_table)
        filter_panel.addWidget(self.search_input, 1)

        self.class_filter = QComboBox()
        self.class_filter.addItem("All")
        # Populate all standard target labels
        from detection.detector import TARGET_CLASSES
        self.class_filter.addItems(sorted(list(set(TARGET_CLASSES.values()))))
        self.class_filter.currentIndexChanged.connect(self.refresh_log_table)
        filter_panel.addWidget(self.class_filter)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_log_table)
        filter_panel.addWidget(self.refresh_btn)

        right_layout.addLayout(filter_panel)

        # Logs Table
        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(4)
        self.logs_table.setHorizontalHeaderLabels(["Timestamp", "Class Label", "Track ID", "Confidence"])
        self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.logs_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.logs_table, 1)

        # Database action buttons
        actions_panel = QHBoxLayout()
        
        self.export_btn = QPushButton("EXPORT CSV REPORT")
        self.export_btn.setId = "export_btn"
        self.export_btn.setObjectName("export_btn")
        self.export_btn.clicked.connect(self.export_logs)
        actions_panel.addWidget(self.export_btn)
        
        self.clear_btn = QPushButton("CLEAR LOGS")
        self.clear_btn.setId = "clear_btn"
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.clicked.connect(self.clear_logs)
        actions_panel.addWidget(self.clear_btn)

        right_layout.addLayout(actions_panel)

        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, 1)

        self.setLayout(main_layout)
        
        # Initial logs load
        self.refresh_log_table()

    def update_perf_chart(self):
        """Timer callback that reads system telemetry and updates charts."""
        # 1. Update CPU and Memory
        cpu_val = psutil.cpu_percent()
        mem_val = psutil.virtual_memory().percent
        
        # Update rolling arrays
        self.cpu_data.pop(0)
        self.cpu_data.append(cpu_val)
        
        self.mem_data.pop(0)
        self.mem_data.append(mem_val)
        
        # 2. Update Plots
        self.cpu_curve.setData(self.time_indices, self.cpu_data)
        self.mem_curve.setData(self.time_indices, self.mem_data)
        self.fps_curve.setData(self.time_indices, self.fps_data)

    def feed_live_fps(self, fps):
        """Called by the main loop to push the latest FPS to chart."""
        self.fps_data.pop(0)
        self.fps_data.append(fps)

    def feed_live_counts(self, counts):
        """Called by the main loop to push active object counts to chart."""
        p_count = counts.get("person", 0)
        
        # Vehicles
        v_count = sum(counts.get(cls, 0) for cls in ["car", "motorcycle", "bus", "truck"])
        
        # Others
        o_count = sum(counts.get(cls, 0) for cls in ["dog", "cat", "chair", "laptop", "mobile phone"])
        
        self.count_history["person"].pop(0)
        self.count_history["person"].append(p_count)
        
        self.count_history["vehicle"].pop(0)
        self.count_history["vehicle"].append(v_count)
        
        self.count_history["other"].pop(0)
        self.count_history["other"].append(o_count)
        
        # Update Plots
        self.person_curve.setData(self.time_indices, self.count_history["person"])
        self.vehicle_curve.setData(self.time_indices, self.count_history["vehicle"])
        self.other_curve.setData(self.time_indices, self.count_history["other"])

    def refresh_log_table(self):
        """Queries the SQLite database and populates the logs table."""
        search = self.search_input.text()
        filter_cls = self.class_filter.currentText()
        
        try:
            logs = self.db.get_logs(search_query=search, filter_class=filter_cls, limit=50)
            self.logs_table.setRowCount(0)
            
            for row_idx, log in enumerate(logs):
                self.logs_table.insertRow(row_idx)
                
                # Format confidence
                conf_text = f"{int(log['confidence'] * 100)}%"
                
                self.logs_table.setItem(row_idx, 0, QTableWidgetItem(log["timestamp"]))
                self.logs_table.setItem(row_idx, 1, QTableWidgetItem(log["object_name"].upper()))
                self.logs_table.setItem(row_idx, 2, QTableWidgetItem(str(log["track_id"])))
                self.logs_table.setItem(row_idx, 3, QTableWidgetItem(conf_text))
        except Exception as e:
            # Silence error if SQLite is locked during write
            pass

    def export_logs(self):
        """Prompts user to select save file and exports DB to CSV."""
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
        os.makedirs(export_dir, exist_ok=True)
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Detection Logs", os.path.join(export_dir, "surveillance_report.csv"), "CSV Files (*.csv)"
        )
        
        if filepath:
            success = self.db.export_to_csv(filepath)
            if success:
                QMessageBox.information(self, "Export Status", f"Detection report successfully exported to:\n{filepath}")
            else:
                QMessageBox.critical(self, "Export Status", "Failed to export logs. Check folder permissions.")

    def clear_logs(self):
        """Prompts for confirmation and wipes the database table."""
        reply = QMessageBox.question(
            self, "Clear Logs Confirmation",
            "Are you sure you want to permanently clear all database detection logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_logs()
            self.refresh_log_table()
