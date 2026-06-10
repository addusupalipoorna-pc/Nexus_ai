import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
    QFrame, QGridLayout, QTextEdit, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, pyqtSlot

class DashboardPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Master layout: Video Area (Left/Center) + Stats/Alerts (Right)
        master_layout = QHBoxLayout()
        master_layout.setSpacing(15)
        master_layout.setContentsMargins(10, 10, 10, 10)

        # Style QWidget
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-weight: normal;
            }
            /* Control buttons */
            QPushButton#ctrl_start {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton#ctrl_start:hover {
                background-color: #059669;
            }
            QPushButton#ctrl_stop {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton#ctrl_stop:hover {
                background-color: #dc2626;
            }
            QPushButton#ctrl_pause {
                background-color: #f59e0b;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton#ctrl_pause:hover {
                background-color: #d97706;
            }
            QPushButton#ctrl_screenshot, QPushButton#ctrl_rec {
                background-color: #475569;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton#ctrl_screenshot:hover {
                background-color: #64748b;
            }
            QPushButton#ctrl_rec:hover {
                background-color: #64748b;
            }
            QPushButton#ctrl_rec[recording="true"] {
                background-color: #dc2626;
                color: white;
            }
        """)

        # ================= LEFT/CENTER: VIDEO SCREEN =================
        video_area = QWidget()
        video_layout = QVBoxLayout()
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(10)

        # Video Frame container (with high-tech glowing border)
        self.video_frame = QFrame()
        self.video_frame.setFrameShape(QFrame.Shape.Box)
        self.video_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #0ea5e9;
                border-radius: 6px;
                background-color: #020617;
            }
        """)
        
        video_frame_layout = QVBoxLayout()
        video_frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.feed_label = QLabel("FEED OFF-LINE - INITIATE CAMERA CORE")
        self.feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_label.setStyleSheet("color: #475569; font-size: 16px; font-weight: bold; border: none;")
        self.feed_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        video_frame_layout.addWidget(self.feed_label)
        
        self.video_frame.setLayout(video_frame_layout)
        video_layout.addWidget(self.video_frame, 1)

        # Controls under the video
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        self.start_btn = QPushButton("START CORE")
        self.start_btn.setObjectName("ctrl_start")
        controls_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setObjectName("ctrl_pause")
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("STOP FEED")
        self.stop_btn.setObjectName("ctrl_stop")
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("background-color: #334155; max-width: 1px;")
        controls_layout.addWidget(line)

        self.rec_btn = QPushButton("RECORD")
        self.rec_btn.setObjectName("ctrl_rec")
        self.rec_btn.setEnabled(False)
        self.rec_btn.setProperty("recording", "false")
        controls_layout.addWidget(self.rec_btn)

        self.screenshot_btn = QPushButton("SCREENSHOT")
        self.screenshot_btn.setObjectName("ctrl_screenshot")
        self.screenshot_btn.setEnabled(False)
        controls_layout.addWidget(self.screenshot_btn)

        video_layout.addLayout(controls_layout)
        video_area.setLayout(video_layout)
        master_layout.addWidget(video_area, 3)

        # ================= RIGHT PANEL: STATS & ALERTS =================
        right_panel = QWidget()
        right_panel.setStyleSheet("""
            QWidget {
                background-color: #1e293b;
                border-radius: 6px;
            }
            QLabel {
                background-color: transparent;
            }
        """)
        right_panel.setFixedWidth(280)
        
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(15)

        # 1. Live Analytics Card
        stats_label = QLabel("LIVE TELEMETRY")
        stats_label.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid #334155; padding-bottom: 5px;")
        panel_layout.addWidget(stats_label)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)

        stats_grid.addWidget(QLabel("SYS FPS:"), 0, 0)
        self.val_fps = QLabel("0.0")
        self.val_fps.setStyleSheet("color: #f8fafc; font-weight: bold;")
        stats_grid.addWidget(self.val_fps, 0, 1)

        stats_grid.addWidget(QLabel("ACTIVE IDS:"), 1, 0)
        self.val_active = QLabel("0")
        self.val_active.setStyleSheet("color: #f8fafc; font-weight: bold;")
        stats_grid.addWidget(self.val_active, 1, 1)

        stats_grid.addWidget(QLabel("AVG CONF:"), 2, 0)
        self.val_conf = QLabel("0%")
        self.val_conf.setStyleSheet("color: #f8fafc; font-weight: bold;")
        stats_grid.addWidget(self.val_conf, 2, 1)

        panel_layout.addLayout(stats_grid)

        # 2. Object Counter Card
        counter_label = QLabel("OBJECT COUNTS")
        counter_label.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid #334155; padding-bottom: 5px;")
        panel_layout.addWidget(counter_label)

        # Scrollable list for object class counts
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: transparent;")
        
        self.counter_widget = QWidget()
        self.counter_widget.setStyleSheet("background-color: transparent;")
        self.counter_list_layout = QVBoxLayout()
        self.counter_list_layout.setContentsMargins(0, 0, 0, 0)
        self.counter_list_layout.setSpacing(5)
        
        self.counter_widget.setLayout(self.counter_list_layout)
        scroll_area.setWidget(self.counter_widget)
        panel_layout.addWidget(scroll_area, 1)

        # 3. Active Alert Feeds
        alert_label = QLabel("SYSTEM SECURITY ALERTS")
        alert_label.setStyleSheet("color: #f43f5e; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid #f43f5e; padding-bottom: 5px;")
        panel_layout.addWidget(alert_label)

        self.alert_log = QTextEdit()
        self.alert_log.setReadOnly(True)
        self.alert_log.setStyleSheet("""
            QTextEdit {
                background-color: #020617;
                border: 1px solid #f43f5e;
                border-radius: 4px;
                color: #f43f5e;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        panel_layout.addWidget(self.alert_log, 1)

        right_panel.setLayout(panel_layout)
        master_layout.addWidget(right_panel)

        self.setLayout(master_layout)

    @pyqtSlot(np.ndarray)
    def update_frame(self, frame_cv):
        """Converts OpenCV numpy frame to QImage/QPixmap and updates feed_label."""
        # Get frame dimensions
        h, w, ch = frame_cv.shape
        bytes_per_line = ch * w
        
        # Convert BGR (OpenCV) to RGB (Qt)
        rgb_image = cv2.cvtColor(frame_cv, cv2.COLOR_BGR2RGB)
        
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Scale to fit label aspect ratio
        label_w = self.feed_label.width()
        label_h = self.feed_label.height()
        
        pixmap = QPixmap.fromImage(q_img).scaled(
            label_w, label_h, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.feed_label.setPixmap(pixmap)

    @pyqtSlot(dict)
    def update_telemetry(self, stats):
        """Updates right panel telemetry labels and logs alert warning messages."""
        self.val_fps.setText(f"{stats['fps']:.1f}")
        self.val_active.setText(str(stats["active_objects"]))
        self.val_conf.setText(f"{int(stats['avg_confidence'] * 100)}%")
        
        # Update class counts list
        # Remove old widgets
        for i in reversed(range(self.counter_list_layout.count())): 
            self.counter_list_layout.itemAt(i).widget().setParent(None)
            
        counts = stats["class_counts"]
        if not counts:
            lbl = QLabel("No active targets detected")
            lbl.setStyleSheet("color: #64748b; font-style: italic;")
            self.counter_list_layout.addWidget(lbl)
        else:
            for cls_name, count in counts.items():
                row = QWidget()
                row_lay = QHBoxLayout()
                row_lay.setContentsMargins(0, 2, 0, 2)
                
                name_lbl = QLabel(cls_name.upper())
                name_lbl.setStyleSheet("color: #94a3b8;")
                val_lbl = QLabel(str(count))
                val_lbl.setStyleSheet("color: #f8fafc; font-weight: bold;")
                
                row_lay.addWidget(name_lbl)
                row_lay.addStretch()
                row_lay.addWidget(val_lbl)
                row.setLayout(row_lay)
                self.counter_list_layout.addWidget(row)
                
        # Update alerts log
        alerts = stats["alerts"]
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")
        for alert in alerts:
            self.alert_log.append(f"[{time_str}] ALERT: {alert}")
            # Limit lines in text edit to keep it responsive
            cursor = self.alert_log.textCursor()
            if self.alert_log.document().lineCount() > 50:
                self.alert_log.clear()
