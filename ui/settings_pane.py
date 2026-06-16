from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QFileDialog, 
    QSlider, QGroupBox, QFormLayout, QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

class SettingsPane(QWidget):
    # Signals settings dictionary to app coordinator
    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clear_requested = False
        self.enroll_requested = False
        self.init_ui()

    def init_ui(self):
        # Create main layout for the SettingsPane widget
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create the scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # Apply transparent style to the scroll area and its viewport
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        # Create container widget for the scroll area
        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        
        # The actual layout for the settings fields
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Style QWidget components (Obsidian theme)
        scroll_content.setStyleSheet("""
            QWidget {
                background-color: #0B0F19;
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
                color: #00E5FF;
                background-color: rgba(22, 27, 38, 0.6);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                color: #94a3b8;
                font-size: 13px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #0B0F19;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 6px;
                color: #f8fafc;
                min-width: 160px;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:focus {
                border: 1px solid #00E5FF;
            }
            QCheckBox {
                spacing: 8px;
                color: #e2e8f0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                background-color: #0B0F19;
            }
            QCheckBox::indicator:checked {
                background-color: #00E5FF;
                border: 1px solid #00E5FF;
            }
            QSlider::groove:horizontal {
                border: 1px solid rgba(255, 255, 255, 0.08);
                height: 6px;
                background: #0B0F19;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #00E5FF;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QPushButton {
                background-color: #00E5FF;
                color: #0B0F19;
                border: none;
                border-radius: 5px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00B4D8;
            }
            QPushButton#browse_btn {
                background-color: rgba(30, 41, 59, 0.8);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
            QPushButton#browse_btn:hover {
                background-color: #1e293b;
                border: 1px solid #00E5FF;
            }
        """)

        # Title
        title_label = QLabel("NEXUS SYSTEM CONFIGURATION")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00E5FF; letter-spacing: 1px;")
        layout.addWidget(title_label)

        # 1. Camera Input Source Group
        source_group = QGroupBox("Inference Stream Capture Core")
        source_layout = QFormLayout()
        source_layout.setSpacing(10)
        source_layout.setContentsMargins(15, 20, 15, 15)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["Synthetic Simulator", "USB Local Webcam", "Local Video File", "IP RTSP Camera Stream"])
        self.source_combo.setCurrentIndex(1)  # Default: USB Local Webcam
        self.source_combo.currentIndexChanged.connect(self.toggle_source_inputs)
        source_layout.addRow("Video Stream Input:", self.source_combo)

        # Webcam index select
        self.webcam_spin = QSpinBox()
        self.webcam_spin.setRange(0, 9)
        self.webcam_spin.setValue(0)
        self.webcam_spin.valueChanged.connect(self.toggle_source_inputs)
        source_layout.addRow("Local Device Index:", self.webcam_spin)

        # Camera Backend select
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["Auto-Negotiate", "Media Foundation (MSMF)", "DirectShow (DSHOW)"])
        self.backend_combo.setCurrentIndex(0)
        source_layout.addRow("Camera Driver Backend:", self.backend_combo)

        # Video File path / RTSP URL LineEdit
        file_widget = QWidget()
        file_h_layout = QHBoxLayout()
        file_h_layout.setContentsMargins(0, 0, 0, 0)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter file path or rtsp:// stream URL...")
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("browse_btn")
        self.browse_btn.clicked.connect(self.browse_video_file)
        self.browse_btn.setStyleSheet("padding: 6px 12px;")
        
        file_h_layout.addWidget(self.path_input, 1)
        file_h_layout.addWidget(self.browse_btn)
        file_widget.setLayout(file_h_layout)
        source_layout.addRow("Stream Path/URL:", file_widget)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # 2. Model Confidence Slider
        model_group = QGroupBox("Model Inference Settings")
        model_layout = QFormLayout()
        model_layout.setSpacing(10)
        model_layout.setContentsMargins(15, 20, 15, 15)

        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(0, 100)
        self.conf_slider.setValue(25)
        self.conf_slider.setTickInterval(5)
        self.conf_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.conf_slider.valueChanged.connect(self.update_conf_label)
        
        self.conf_val_label = QLabel("0.25")
        self.conf_val_label.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 14px;")
        
        conf_h_widget = QWidget()
        conf_h_layout = QHBoxLayout()
        conf_h_layout.setContentsMargins(0, 0, 0, 0)
        conf_h_layout.addWidget(self.conf_slider, 1)
        conf_h_layout.addWidget(self.conf_val_label)
        conf_h_widget.setLayout(conf_h_layout)
        
        model_layout.addRow("Confidence Min:", conf_h_widget)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # 3. GUI Visualization switches
        vis_group = QGroupBox("Visual HUD Toggles")
        vis_layout = QFormLayout()
        vis_layout.setSpacing(12)
        vis_layout.setContentsMargins(15, 20, 15, 15)

        self.cb_trails = QCheckBox("Render Fading Bounding Box Trails")
        self.cb_trails.setChecked(True)
        vis_layout.addRow("", self.cb_trails)

        self.cb_labels = QCheckBox("Draw Classification Labels & Scores")
        self.cb_labels.setChecked(True)
        vis_layout.addRow("", self.cb_labels)

        self.cb_intrusion = QCheckBox("Superimpose Polygon Intrusion Zone")
        self.cb_intrusion.setChecked(True)
        vis_layout.addRow("", self.cb_intrusion)

        self.cb_multicam = QCheckBox("Enable Multi-Camera Surveillance Wall (2x2 Grid)")
        self.cb_multicam.setChecked(False)
        vis_layout.addRow("", self.cb_multicam)

        self.cb_heatmap = QCheckBox("Superimpose AI Activity Density Heatmap")
        self.cb_heatmap.setChecked(False)
        vis_layout.addRow("", self.cb_heatmap)

        vis_group.setLayout(vis_layout)
        layout.addWidget(vis_group)

        # 4. Air Writing Canvas settings
        canvas_group = QGroupBox("Air Writing Canvas Designer")
        canvas_layout = QFormLayout()
        canvas_layout.setSpacing(10)
        canvas_layout.setContentsMargins(15, 20, 15, 15)
        
        self.color_combo = QComboBox()
        self.color_combo.addItems([
            "Neon Green",
            "Electric Cyan", 
            "Hot Pink", 
            "Crimson Red", 
            "Sun Yellow", 
            "Bright White"
        ])
        self.color_combo.setCurrentIndex(0)
        canvas_layout.addRow("Brush Color:", self.color_combo)
        
        self.brush_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.brush_size_slider.setRange(1, 15)
        self.brush_size_slider.setValue(4)
        self.brush_size_slider.valueChanged.connect(self.update_brush_size_label)
        
        self.brush_size_val_label = QLabel("4 px")
        self.brush_size_val_label.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 13px;")
        
        size_h_widget = QWidget()
        size_h_layout = QHBoxLayout()
        size_h_layout.setContentsMargins(0, 0, 0, 0)
        size_h_layout.addWidget(self.brush_size_slider, 1)
        size_h_layout.addWidget(self.brush_size_val_label)
        size_h_widget.setLayout(size_h_layout)
        canvas_layout.addRow("Brush Size:", size_h_widget)
        
        self.btn_clear_canvas = QPushButton("CLEAR WRITING CANVAS")
        self.btn_clear_canvas.clicked.connect(self.clear_canvas_action)
        self.btn_clear_canvas.setStyleSheet("background-color: rgba(239, 68, 68, 0.2); border: 1px solid #EF4444; color: #EF4444; padding: 6px; font-weight: bold;")
        canvas_layout.addRow(self.btn_clear_canvas)
        
        canvas_group.setLayout(canvas_layout)
        layout.addWidget(canvas_group)

        # 5. Face registry settings
        face_group = QGroupBox("Facial Recognition Registry")
        face_layout = QFormLayout()
        face_layout.setSpacing(10)
        face_layout.setContentsMargins(15, 20, 15, 15)
        
        self.face_name_input = QLineEdit()
        self.face_name_input.setPlaceholderText("Enter subject name...")
        face_layout.addRow("Enroll Name:", self.face_name_input)
        
        self.btn_enroll_face = QPushButton("ENROLL FACE LANDMARKS")
        self.btn_enroll_face.clicked.connect(self.enroll_face_action)
        self.btn_enroll_face.setStyleSheet("background-color: rgba(0, 229, 255, 0.2); border: 1px solid #00E5FF; color: #00E5FF; padding: 6px; font-weight: bold;")
        face_layout.addRow(self.btn_enroll_face)
        
        face_group.setLayout(face_layout)
        layout.addWidget(face_group)

        # 6. Notifier settings
        notifier_group = QGroupBox("NEXUS AI Alert Dispatcher")
        notifier_layout = QFormLayout()
        notifier_layout.setSpacing(10)
        notifier_layout.setContentsMargins(15, 20, 15, 15)
        
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setPlaceholderText("Enter Telegram Bot Token...")
        notifier_layout.addRow("Telegram Bot Token:", self.telegram_token_input)
        
        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setPlaceholderText("Enter Telegram Chat ID...")
        notifier_layout.addRow("Telegram Chat ID:", self.telegram_chat_id_input)
        
        self.email_smtp_server_input = QLineEdit("smtp.gmail.com")
        notifier_layout.addRow("SMTP Server:", self.email_smtp_server_input)
        
        self.email_smtp_port_spin = QSpinBox()
        self.email_smtp_port_spin.setRange(1, 65535)
        self.email_smtp_port_spin.setValue(587)
        notifier_layout.addRow("SMTP Port:", self.email_smtp_port_spin)
        
        self.email_sender_input = QLineEdit()
        self.email_sender_input.setPlaceholderText("sender@example.com")
        notifier_layout.addRow("Email Sender Address:", self.email_sender_input)
        
        self.email_password_input = QLineEdit()
        self.email_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_password_input.setPlaceholderText("Sender app password...")
        notifier_layout.addRow("Email Sender Password:", self.email_password_input)
        
        self.email_recipient_input = QLineEdit()
        self.email_recipient_input.setPlaceholderText("recipient@example.com")
        notifier_layout.addRow("Email Recipient Address:", self.email_recipient_input)
        
        notifier_group.setLayout(notifier_layout)
        layout.addWidget(notifier_group)

        # Save Settings
        self.apply_btn = QPushButton("COMMIT CORE SETTINGS")
        self.apply_btn.clicked.connect(self.dispatch_settings)
        layout.addWidget(self.apply_btn)
        
        layout.addStretch()
        scroll_content.setLayout(layout)
        scroll_area.setWidget(scroll_content)
        
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
        
        # Align all labels across group boxes for perfect visual alignment
        self.align_labels()
        
        # Initialize input toggles
        self.toggle_source_inputs()

    def update_conf_label(self, val):
        self.conf_val_label.setText(f"{val/100.0:.2f}")

    def update_brush_size_label(self, val):
        self.brush_size_val_label.setText(f"{val} px")

    def clear_canvas_action(self):
        self.clear_requested = True
        self.dispatch_settings()
        self.clear_requested = False

    def enroll_face_action(self):
        self.enroll_requested = True
        self.dispatch_settings()
        self.enroll_requested = False

    def toggle_source_inputs(self):
        index = self.source_combo.currentIndex()
        # 0: Synthetic, 1: Webcam, 2: File, 3: RTSP
        self.webcam_spin.setEnabled(index == 1)
        self.backend_combo.setEnabled(index == 1)
        self.path_input.setEnabled(index in [2, 3])
        self.browse_btn.setEnabled(index == 2)
        if index == 1:
            self.path_input.setText(str(self.webcam_spin.value()))

    def browse_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        if file_path:
            self.path_input.setText(file_path)

    def dispatch_settings(self):
        """Assembles settings dict and emits settings_changed signal."""
        idx = self.source_combo.currentIndex()
        source_type = "synthetic"
        source_path = "0"
        
        if idx == 0:
            source_type = "synthetic"
            source_path = "0"
        elif idx == 1:
            source_type = "webcam"
            source_path = str(self.webcam_spin.value())
        elif idx == 2:
            source_type = "file"
            source_path = self.path_input.text()
        elif idx == 3:
            source_type = "rtsp"
            source_path = self.path_input.text()

        # Color mapping (BGR format for OpenCV drawing)
        color_map = {
            "Neon Green": (0, 255, 0),
            "Electric Cyan": (255, 229, 0),
            "Hot Pink": (180, 0, 255),
            "Crimson Red": (60, 0, 255),
            "Sun Yellow": (0, 229, 255),
            "Bright White": (255, 255, 255)
        }
        selected_color_name = self.color_combo.currentText()
        selected_color_bgr = color_map.get(selected_color_name, (0, 255, 0))
            
        backend_map = {
            0: "auto",
            1: "msmf",
            2: "dshow"
        }
        camera_backend = backend_map.get(self.backend_combo.currentIndex(), "auto")

        settings = {
            "source_type": source_type,
            "source_path": source_path,
            "camera_backend": camera_backend,
            "conf_threshold": self.conf_slider.value() / 100.0,
            "show_trails": self.cb_trails.isChecked(),
            "show_labels": self.cb_labels.isChecked(),
            "show_intrusion": self.cb_intrusion.isChecked(),
            "multi_camera": self.cb_multicam.isChecked(),
            "show_heatmap": self.cb_heatmap.isChecked(),
            "brush_color": selected_color_bgr,
            "brush_thickness": self.brush_size_slider.value(),
            "clear_canvas": self.clear_requested,
            "register_face_name": self.face_name_input.text().strip() if self.enroll_requested else "",
            "telegram_token": self.telegram_token_input.text().strip(),
            "telegram_chat_id": self.telegram_chat_id_input.text().strip(),
            "email_smtp_server": self.email_smtp_server_input.text().strip(),
            "email_smtp_port": self.email_smtp_port_spin.value(),
            "email_sender": self.email_sender_input.text().strip(),
            "email_password": self.email_password_input.text(),
            "email_recipient": self.email_recipient_input.text().strip()
        }
        self.settings_changed.emit(settings)

    def align_labels(self):
        """Standardizes all form layout label column widths and right-aligns them for perfect alignment."""
        for group_box in self.findChildren(QGroupBox):
            layout = group_box.layout()
            if isinstance(layout, QFormLayout):
                layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
                for row in range(layout.rowCount()):
                    label_item = layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
                    if label_item:
                        widget = label_item.widget()
                        if widget:
                            widget.setMinimumWidth(160)
                            widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
