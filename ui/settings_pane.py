from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QFileDialog, 
    QSlider, QGroupBox, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

class SettingsPane(QWidget):
    # Signals settings dictionary to app coordinator
    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Style QWidget components (Obsidian theme)
        self.setStyleSheet("""
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
        self.source_combo.setCurrentIndex(0)  # Default: Synthetic Simulator
        self.source_combo.currentIndexChanged.connect(self.toggle_source_inputs)
        source_layout.addRow("Video Stream Input:", self.source_combo)

        # Webcam index select
        self.webcam_spin = QSpinBox()
        self.webcam_spin.setRange(0, 9)
        self.webcam_spin.setValue(0)
        self.webcam_spin.valueChanged.connect(self.toggle_source_inputs)
        source_layout.addRow("Local Device Index:", self.webcam_spin)

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
        vis_layout = QVBoxLayout()
        vis_layout.setSpacing(12)
        vis_layout.setContentsMargins(15, 20, 15, 15)

        self.cb_trails = QCheckBox("Render Fading Bounding Box Trails")
        self.cb_trails.setChecked(True)
        vis_layout.addWidget(self.cb_trails)

        self.cb_labels = QCheckBox("Draw Classification Labels & Scores")
        self.cb_labels.setChecked(True)
        vis_layout.addWidget(self.cb_labels)

        self.cb_intrusion = QCheckBox("Superimpose Polygon Intrusion Zone")
        self.cb_intrusion.setChecked(True)
        vis_layout.addWidget(self.cb_intrusion)

        vis_group.setLayout(vis_layout)
        layout.addWidget(vis_group)

        # Save Settings
        self.apply_btn = QPushButton("COMMIT CORE SETTINGS")
        self.apply_btn.clicked.connect(self.dispatch_settings)
        layout.addWidget(self.apply_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Initialize input toggles
        self.toggle_source_inputs()

    def update_conf_label(self, val):
        self.conf_val_label.setText(f"{val/100.0:.2f}")

    def toggle_source_inputs(self):
        index = self.source_combo.currentIndex()
        # 0: Synthetic, 1: Webcam, 2: File, 3: RTSP
        self.webcam_spin.setEnabled(index == 1)
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
            
        settings = {
            "source_type": source_type,
            "source_path": source_path,
            "conf_threshold": self.conf_slider.value() / 100.0,
            "show_trails": self.cb_trails.isChecked(),
            "show_labels": self.cb_labels.isChecked(),
            "show_intrusion": self.cb_intrusion.isChecked()
        }
        self.settings_changed.emit(settings)
