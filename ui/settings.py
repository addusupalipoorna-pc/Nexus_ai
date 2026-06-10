from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QFileDialog, 
    QSlider, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

class SettingsPanel(QWidget):
    # Signal emitted when settings are updated
    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Style QWidget
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
                color: #38bdf8;
                background-color: #1e293b;
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
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #0f172a;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 6px;
                color: #f8fafc;
                min-width: 150px;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border: 1px solid #38bdf8;
            }
            QComboBox::drop-down {
                border: none;
            }
            QCheckBox {
                spacing: 8px;
                color: #e2e8f0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #475569;
                border-radius: 4px;
                background-color: #0f172a;
            }
            QCheckBox::indicator:checked {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                image: url(check.png); /* Fallback */
            }
            QSlider::groove:horizontal {
                border: 1px solid #475569;
                height: 6px;
                background: #0f172a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #38bdf8;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QPushButton {
                background-color: #0ea5e9;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
            QPushButton:pressed {
                background-color: #0369a1;
            }
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #475569;
                border-radius: 4px;
                color: white;
                padding: 6px;
            }
        """)

        # Title
        title_label = QLabel("SYSTEM CONFIGURATION")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        layout.addWidget(title_label)

        # 1. Camera Source Configuration Group
        source_group = QGroupBox("Camera & Video Source")
        source_layout = QFormLayout()
        source_layout.setSpacing(10)
        source_layout.setContentsMargins(15, 20, 15, 15)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["Synthetic Simulator", "USB Webcam", "Local Video File"])
        self.source_combo.setCurrentIndex(1)  # Default to USB Webcam
        self.source_combo.currentIndexChanged.connect(self.toggle_source_inputs)
        source_layout.addRow("Input Source:", self.source_combo)

        # Camera Index (Webcam)
        self.cam_idx_spin = QSpinBox()
        self.cam_idx_spin.setRange(0, 9)
        self.cam_idx_spin.setValue(0)
        source_layout.addRow("Webcam Index:", self.cam_idx_spin)

        # Video File path layout
        video_file_widget = QWidget()
        video_file_layout = QHBoxLayout()
        video_file_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_path_label = QLabel("None")
        self.video_path_label.setStyleSheet("border: 1px solid #475569; padding: 6px; border-radius: 4px; background-color: #0f172a;")
        self.video_path_label.setWordWrap(False)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_video_file)
        self.browse_btn.setStyleSheet("padding: 6px 12px; background-color: #475569;")
        
        video_file_layout.addWidget(self.video_path_label, 1)
        video_file_layout.addWidget(self.browse_btn)
        video_file_widget.setLayout(video_file_layout)
        source_layout.addRow("Video File:", video_file_widget)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # 2. AI Model Settings Group
        model_group = QGroupBox("YOLOv8 Detection Settings")
        model_layout = QFormLayout()
        model_layout.setSpacing(10)
        model_layout.setContentsMargins(15, 20, 15, 15)

        # Confidence Threshold Slider
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(5, 95)
        self.conf_slider.setValue(25)
        self.conf_slider.setTickInterval(5)
        self.conf_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        
        self.conf_val_label = QLabel("25%")
        self.conf_slider.valueChanged.connect(self.update_conf_label)
        
        conf_widget = QWidget()
        conf_layout = QHBoxLayout()
        conf_layout.setContentsMargins(0, 0, 0, 0)
        conf_layout.addWidget(self.conf_slider, 1)
        conf_layout.addWidget(self.conf_val_label)
        conf_widget.setLayout(conf_layout)
        
        model_layout.addRow("Confidence Min:", conf_widget)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # 3. Tracking Options Group
        track_group = QGroupBox("Deep SORT Tracking Options")
        track_layout = QFormLayout()
        track_layout.setSpacing(12)
        track_layout.setContentsMargins(15, 20, 15, 15)

        self.cb_show_trails = QCheckBox("Draw Movement Trails")
        self.cb_show_trails.setChecked(True)
        track_layout.addRow(self.cb_show_trails)

        self.cb_show_heatmap = QCheckBox("Draw Intensity Heatmap")
        self.cb_show_heatmap.setChecked(False)
        self.cb_show_heatmap.stateChanged.connect(self.toggle_heatmap_inputs)
        track_layout.addRow(self.cb_show_heatmap)

        # Heatmap opacity slider
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(40)
        self.opacity_slider.setEnabled(False)
        
        self.opacity_val_label = QLabel("40%")
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        
        opac_widget = QWidget()
        opac_layout = QHBoxLayout()
        opac_layout.setContentsMargins(0, 0, 0, 0)
        opac_layout.addWidget(self.opacity_slider, 1)
        opac_layout.addWidget(self.opacity_val_label)
        opac_widget.setLayout(opac_layout)
        track_layout.addRow("Heatmap Opacity:", opac_widget)

        track_group.setLayout(track_layout)
        layout.addWidget(track_group)

        # 4. Smart Alerts Group
        alert_group = QGroupBox("Smart Alert Policies")
        alert_layout = QFormLayout()
        alert_layout.setSpacing(12)
        alert_layout.setContentsMargins(15, 20, 15, 15)

        self.alert_person_spin = QSpinBox()
        self.alert_person_spin.setRange(1, 100)
        self.alert_person_spin.setValue(5)
        alert_layout.addRow("Person Count Limit:", self.alert_person_spin)

        self.cb_alert_vehicle = QCheckBox("Alert on Vehicle Detections")
        self.cb_alert_vehicle.setChecked(False)
        alert_layout.addRow(self.cb_alert_vehicle)

        self.cb_alert_unknown = QCheckBox("Alert on Unknown Objects")
        self.cb_alert_unknown.setChecked(False)
        alert_layout.addRow(self.cb_alert_unknown)

        alert_group.setLayout(alert_layout)
        layout.addWidget(alert_group)

        # Save Settings Button
        self.save_btn = QPushButton("APPLY SYSTEM SETTINGS")
        self.save_btn.clicked.connect(self.apply_settings)
        layout.addWidget(self.save_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Initial call to toggle inputs properly
        self.toggle_source_inputs()

    def update_conf_label(self, val):
        self.conf_val_label.setText(f"{val}%")

    def update_opacity_label(self, val):
        self.opacity_val_label.setText(f"{val}%")

    def toggle_source_inputs(self):
        index = self.source_combo.currentIndex()
        # 0: Synthetic, 1: Webcam, 2: File
        self.cam_idx_spin.setEnabled(index == 1)
        self.browse_btn.setEnabled(index == 2)
        
    def toggle_heatmap_inputs(self, state):
        self.opacity_slider.setEnabled(state == 2) # Qt.CheckState.Checked

    def browse_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        if file_path:
            self.video_path_label.setText(file_path)

    def apply_settings(self):
        # Package settings into a dict and emit it
        source_idx = self.source_combo.currentIndex()
        source_type = "synthetic"
        source_val = 0
        
        if source_idx == 1:
            source_type = "webcam"
            source_val = self.cam_idx_spin.value()
        elif source_idx == 2:
            source_type = "file"
            source_val = self.video_path_label.text()
            
        settings = {
            "source_type": source_type,
            "source_val": source_val,
            "conf_threshold": self.conf_slider.value() / 100.0,
            "show_trails": self.cb_show_trails.isChecked(),
            "show_heatmap": self.cb_show_heatmap.isChecked(),
            "heatmap_opacity": self.opacity_slider.value() / 100.0,
            "alert_person_threshold": self.alert_person_spin.value(),
            "alert_vehicle_detect": self.cb_alert_vehicle.isChecked(),
            "alert_unknown_detect": self.cb_alert_unknown.isChecked()
        }
        self.settings_changed.emit(settings)
