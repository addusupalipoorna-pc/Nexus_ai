import sys
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QLabel, QFrame, QStackedWidget, QSizePolicy, QScrollArea, QTextEdit
)
from PyQt6.QtCore import Qt, QPoint, pyqtSlot
from PyQt6.QtGui import QColor, QFont

from ui.video_canvas import VideoCanvas
from ui.analytics_hub import AnalyticsHub
from ui.settings_pane import SettingsPane
from core.engine import InferenceEngine
from database.logger import DatabaseLogger

class CustomTitleBar(QFrame):
    """Custom title bar for the frameless window, handling drags and close/min/max clicks."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_win = parent
        self.drag_position = QPoint()
        
        self.setFixedHeight(35)
        self.setStyleSheet("""
            QFrame {
                background-color: #0E131F;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1.5px;
                background-color: transparent;
                border: none;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #94a3b8;
                width: 35px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #00E5FF;
            }
            QPushButton#btn_close:hover {
                background-color: #FF003C;
                color: white;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo Icon
        self.title_label = QLabel("NEXUS AI // SURVEILLANCE & MULTI-OBJECT TRACKING CONSOLE")
        layout.addWidget(self.title_label)
        layout.addStretch()
        
        # Minimize button
        self.btn_min = QPushButton("-")
        self.btn_min.clicked.connect(self.minimize_window)
        layout.addWidget(self.btn_min)
        
        # Maximize button
        self.btn_max = QPushButton("口")
        self.btn_max.clicked.connect(self.maximize_window)
        layout.addWidget(self.btn_max)
        
        # Close button
        self.btn_close = QPushButton("X")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.clicked.connect(self.close_window)
        layout.addWidget(self.btn_close)
        
        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent_win.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.parent_win.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def minimize_window(self):
        self.parent_win.showMinimized()

    def maximize_window(self):
        if self.parent_win.isMaximized():
            self.parent_win.showNormal()
        else:
            self.parent_win.showMaximized()

    def close_window(self):
        self.parent_win.close()


class MainWindow(QMainWindow):
    def __init__(self, db_logger: DatabaseLogger, engine: InferenceEngine):
        super().__init__()
        self.db = db_logger
        self.engine = engine
        
        # Setup frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        self.resize(1300, 850)
        
        # Core views instantiation
        self.canvas = VideoCanvas()
        self.view_analytics = AnalyticsHub(self.db.get_db_path())
        self.view_settings = SettingsPane()
        
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # Shell container containing Title Bar + Content Area
        shell_widget = QWidget()
        shell_widget.setObjectName("shell")
        shell_layout = QVBoxLayout()
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        shell_widget.setLayout(shell_layout)
        self.setCentralWidget(shell_widget)

        # Style shell
        shell_widget.setStyleSheet("""
            QWidget#shell {
                background-color: #0B0F19;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)

        # Add Custom Title Bar
        self.title_bar = CustomTitleBar(self)
        shell_layout.addWidget(self.title_bar)

        # Main Area (Sidebar + QStackedWidget)
        main_content = QWidget()
        main_content_layout = QHBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        main_content.setLayout(main_content_layout)
        shell_layout.addWidget(main_content)

        # ================= SIDEBAR NAVIGATOR =================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: #0E131F;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
            }
            QLabel#nav_header {
                font-size: 16px;
                font-weight: bold;
                color: #00E5FF;
                letter-spacing: 2px;
                padding: 20px 15px 5px 15px;
            }
            QLabel#nav_subheader {
                font-size: 9px;
                color: #64748b;
                letter-spacing: 1px;
                padding: 0px 15px 25px 15px;
            }
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                border-left: 3px solid transparent;
                padding: 14px 18px;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: rgba(22, 27, 38, 0.6);
                color: #00E5FF;
            }
            QPushButton[active="true"] {
                background-color: rgba(22, 27, 38, 0.6);
                color: #00E5FF;
                border-left: 3px solid #00E5FF;
            }
        """)
        
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(1)
        
        # Header
        nav_title = QLabel("NEXUS CORE")
        nav_title.setObjectName("nav_header")
        sidebar_layout.addWidget(nav_title)
        
        nav_sub = QLabel("SURVEILLANCE NODE")
        nav_sub.setObjectName("nav_subheader")
        sidebar_layout.addWidget(nav_sub)

        # Buttons
        self.btn_dash = QPushButton("LIVE SURVEILLANCE")
        self.btn_dash.setProperty("active", "true")
        self.btn_dash.clicked.connect(lambda: self.switch_page(0))
        sidebar_layout.addWidget(self.btn_dash)

        self.btn_analytics = QPushButton("ANALYTICS HUB")
        self.btn_analytics.setProperty("active", "false")
        self.btn_analytics.clicked.connect(lambda: self.switch_page(1))
        sidebar_layout.addWidget(self.btn_analytics)

        self.btn_settings = QPushButton("CORE SETTINGS")
        self.btn_settings.setProperty("active", "false")
        self.btn_settings.clicked.connect(lambda: self.switch_page(2))
        sidebar_layout.addWidget(self.btn_settings)

        sidebar_layout.addStretch()

        # System healthy label
        self.lbl_healthy = QLabel("SYSTEM: SECURED")
        self.lbl_healthy.setStyleSheet("color: #10B981; font-size: 10px; font-weight: bold; padding: 15px;")
        sidebar_layout.addWidget(self.lbl_healthy)

        sidebar.setLayout(sidebar_layout)
        main_content_layout.addWidget(sidebar)

        # ================= STACKED PAGE CONTAINER =================
        self.stacked_widget = QStackedWidget()
        main_content_layout.addWidget(self.stacked_widget, 1)

        # Page 0: Live Surveillance Dashboard layout
        self.page_surveillance = QWidget()
        dash_layout = QHBoxLayout()
        dash_layout.setSpacing(15)
        dash_layout.setContentsMargins(15, 15, 15, 15)
        self.page_surveillance.setLayout(dash_layout)

        # Left Column: Video display Canvas + controls underneath
        video_area = QWidget()
        video_layout = QVBoxLayout()
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(10)
        
        # Add our OpenGL Video canvas
        video_layout.addWidget(self.canvas, 1)
        
        # Canvas Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # Control Buttons styling
        ctrl_styles = """
            QPushButton {
                background-color: rgba(22, 27, 38, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                color: #e2e8f0;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 1px solid #00E5FF;
                color: #00E5FF;
            }
            QPushButton#btn_start {
                background-color: rgba(16, 185, 129, 0.15);
                border: 1px solid #10B981;
                color: #10B981;
            }
            QPushButton#btn_start:hover {
                background-color: #10B981;
                color: #0B0F19;
            }
            QPushButton#btn_stop {
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid #EF4444;
                color: #EF4444;
            }
            QPushButton#btn_stop:hover {
                background-color: #EF4444;
                color: #0B0F19;
            }
            QPushButton#btn_rec[recording="true"] {
                background-color: #FF003C;
                border: 1px solid #FF003C;
                color: white;
            }
        """
        video_area.setStyleSheet(ctrl_styles)

        self.btn_start = QPushButton("START CORE")
        self.btn_start.setObjectName("btn_start")
        controls_layout.addWidget(self.btn_start)

        self.btn_pause = QPushButton("PAUSE")
        self.btn_pause.setEnabled(False)
        controls_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("OFFLINE FEED")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        controls_layout.addWidget(self.btn_stop)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-width: 1px;")
        controls_layout.addWidget(line)

        self.btn_rec = QPushButton("RECORD MP4")
        self.btn_rec.setObjectName("btn_rec")
        self.btn_rec.setEnabled(False)
        self.btn_rec.setProperty("recording", "false")
        controls_layout.addWidget(self.btn_rec)

        self.btn_shot = QPushButton("SNAPSHOT")
        self.btn_shot.setEnabled(False)
        controls_layout.addWidget(self.btn_shot)

        video_layout.addLayout(controls_layout)
        video_area.setLayout(video_layout)
        dash_layout.addWidget(video_area, 3)

        # Right Column: Live Telemetry telemetry & alarms HUD panel
        right_panel = QFrame()
        right_panel.setFixedWidth(280)
        right_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(22, 27, 38, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(15)

        # Telemetry Card
        t_title = QLabel("LIVE HUD TELEMETRY")
        t_title.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 5px;")
        panel_layout.addWidget(t_title)

        telemetry_layout = QVBoxLayout()
        telemetry_layout.setSpacing(8)
        
        self.lbl_latency = QLabel("LATENCY: 0.0 ms")
        self.lbl_fps = QLabel("SYS FPS: 0.0")
        self.lbl_active = QLabel("ACTIVE TRACKS: 0")
        
        for lbl in [self.lbl_latency, self.lbl_fps, self.lbl_active]:
            lbl.setStyleSheet("color: #f8fafc; font-weight: bold; font-family: monospace; font-size: 13px;")
            telemetry_layout.addWidget(lbl)
            
        panel_layout.addLayout(telemetry_layout)

        # Itemized Targets Counts
        counts_title = QLabel("TRACKED TARGETS")
        counts_title.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 5px;")
        panel_layout.addWidget(counts_title)

        # Scroll area for counts
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: transparent;")
        
        self.counts_widget = QWidget()
        self.counts_widget.setStyleSheet("background-color: transparent;")
        self.counts_list_layout = QVBoxLayout()
        self.counts_list_layout.setContentsMargins(0, 0, 0, 0)
        self.counts_list_layout.setSpacing(5)
        self.counts_widget.setLayout(self.counts_list_layout)
        scroll_area.setWidget(self.counts_widget)
        panel_layout.addWidget(scroll_area, 1)

        # Alarm HUD Alerts list
        a_title = QLabel("SECURITY EVENTS HUD")
        a_title.setStyleSheet("color: #FF003C; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid #FF003C; padding-bottom: 5px;")
        panel_layout.addWidget(a_title)

        self.alarm_text = QTextEdit()
        self.alarm_text.setReadOnly(True)
        self.alarm_text.setStyleSheet("""
            QTextEdit {
                background-color: #020617;
                border: 1px solid #FF003C;
                border-radius: 4px;
                color: #FF003C;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        panel_layout.addWidget(self.alarm_text, 1)

        right_panel.setLayout(panel_layout)
        dash_layout.addWidget(right_panel)

        # Add Pages to Stack
        self.stacked_widget.addWidget(self.page_surveillance)
        self.stacked_widget.addWidget(self.view_analytics)
        self.stacked_widget.addWidget(self.view_settings)

        # Initialize buttons style properties
        self._update_sidebar_styling()

    def connect_signals(self):
        # 1. UI Control Actions
        self.btn_start.clicked.connect(self.start_core)
        self.btn_stop.clicked.connect(self.stop_core)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_shot.clicked.connect(lambda: self.engine.trigger_screenshot("annotated"))
        self.btn_rec.clicked.connect(self.toggle_recording)

        # 2. Engine Signals
        self.engine.frame_ready.connect(self.handle_frame_packet)
        self.engine.telemetry_ready.connect(self.handle_telemetry_packet)
        
        # 3. Settings Changed
        self.view_settings.settings_changed.connect(self.engine.apply_settings)

    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        
        # Update active flags
        self.btn_dash.setProperty("active", "true" if index == 0 else "false")
        self.btn_analytics.setProperty("active", "true" if index == 1 else "false")
        self.btn_settings.setProperty("active", "true" if index == 2 else "false")
        
        self._update_sidebar_styling()
        
        # Refresh analytics when switching to it
        if index == 1:
            self.view_analytics.refresh_database_grid()

    def _update_sidebar_styling(self):
        # Trigger redraw of QSS styles
        for btn in [self.btn_dash, self.btn_analytics, self.btn_settings]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def start_core(self):
        """Launches QThread inference engine."""
        if not self.engine.isRunning():
            self.engine.start()
            
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_pause.setEnabled(True)
            self.btn_rec.setEnabled(True)
            self.btn_shot.setEnabled(True)
            
            self.lbl_healthy.setText("SYSTEM: MONITORING")
            self.lbl_healthy.setStyleSheet("color: #00E5FF; font-size: 10px; font-weight: bold; padding: 15px;")

    def stop_core(self):
        """Shuts down QThread inference engine safely."""
        if self.engine.isRunning():
            self.lbl_healthy.setText("SYSTEM: STANDBY")
            self.lbl_healthy.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; padding: 15px;")
            
            # Request stop and join
            self.engine.is_running = False
            self.engine.wait()
            
            # Reset Controls
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_rec.setEnabled(False)
            self.btn_shot.setEnabled(False)
            
            self.btn_pause.setText("PAUSE")
            
            # Stop recording if active
            self.engine.stop_recording()
            self.btn_rec.setText("RECORD MP4")
            self.btn_rec.setProperty("recording", "false")
            self.btn_rec.style().unpolish(self.btn_rec)
            self.btn_rec.style().polish(self.btn_rec)
            
            self.canvas.clear_canvas()
            
            # Update labels
            self.lbl_latency.setText("LATENCY: 0.0 ms")
            self.lbl_fps.setText("SYS FPS: 0.0")
            self.lbl_active.setText("ACTIVE TRACKS: 0")
            
            # Clear counts list
            for i in reversed(range(self.counts_list_layout.count())): 
                self.counts_list_layout.itemAt(i).widget().setParent(None)

    def toggle_pause(self):
        if self.engine.isRunning():
            is_paused = not self.engine.is_paused
            self.engine.is_paused = is_paused
            if is_paused:
                self.btn_pause.setText("RESUME")
            else:
                self.btn_pause.setText("PAUSE")

    def toggle_recording(self):
        if self.engine.isRunning():
            is_rec = not self.engine.is_recording
            if is_rec:
                self.engine.start_recording()
                self.btn_rec.setText("STOP RECORD")
                self.btn_rec.setProperty("recording", "true")
            else:
                self.engine.stop_recording()
                self.btn_rec.setText("RECORD MP4")
                self.btn_rec.setProperty("recording", "false")
                
            self.btn_rec.style().unpolish(self.btn_rec)
            self.btn_rec.style().polish(self.btn_rec)

    @pyqtSlot(object, dict)
    def handle_frame_packet(self, frame, payload):
        """Processes signals containing painted frame array and HUD metadata dictionary."""
        # 1. Update OpenGL painting canvas
        self.canvas.set_frame(frame)
        
        # 2. Update telemetry labels
        active_objects = payload["active_objects"]
        self.lbl_active.setText(f"ACTIVE TRACKS: {len(active_objects)}")
        
        # 3. Update target classification counts list
        # Group counts by class
        counts = {}
        for obj_id, info in active_objects.items():
            cls_name = info["class"]
            counts[cls_name] = counts.get(cls_name, 0) + 1
            
        # Clean counts widgets
        for i in reversed(range(self.counts_list_layout.count())): 
            self.counts_list_layout.itemAt(i).widget().setParent(None)
            
        if not counts:
            lbl = QLabel("No active targets detected")
            lbl.setStyleSheet("color: #64748b; font-style: italic;")
            self.counts_list_layout.addWidget(lbl)
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
                self.counts_list_layout.addWidget(row)
                
        # 4. Handle Intrusion alarm violations
        if payload["intrusion_alert"]:
            from datetime import datetime
            time_str = datetime.now().strftime("%H:%M:%S")
            self.alarm_text.append(f"[{time_str}] ZONE INTRUSION ALERT DETECTED")
            # Play beep sound asynchronously in a background thread to prevent UI thread lag
            try:
                import threading
                def play_beep():
                    try:
                        import winsound
                        winsound.Beep(1800, 100)
                    except Exception:
                        pass
                threading.Thread(target=play_beep, daemon=True).start()
            except Exception:
                pass
            
            # Limit alarm text capacity
            if self.alarm_text.document().lineCount() > 50:
                self.alarm_text.clear()

    @pyqtSlot(float, float)
    def handle_telemetry_packet(self, latency_ms, fps):
        """Processes latency and FPS values from the engine thread."""
        self.lbl_latency.setText(f"LATENCY: {latency_ms:.1f} ms")
        self.lbl_fps.setText(f"SYS FPS: {fps:.1f}")
        
        # Send telemetry to Analytics hub rolling charts
        self.view_analytics.feed_live_latency(latency_ms)

    def closeEvent(self, event):
        """Wipes threads on window close events."""
        self.stop_core()
        event.accept()
