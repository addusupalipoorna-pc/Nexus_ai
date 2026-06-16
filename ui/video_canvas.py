import numpy as np
import cv2
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QPainter, QImage, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QRect, QTimer, QPoint

class VideoCanvas(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.setStyleSheet("background-color: #020617; border: 2px solid #00E5FF; border-radius: 6px;")
        
        # Scan animation state
        self.scan_ticks = -1
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.update_scan)

        # Camera flash animation state
        self.flash_alpha = 0
        self.flash_timer_obj = None
        
        # Reference to InferenceEngine (attached by MainWindow)
        self.engine = None
        
    def update_scan(self):
        self.scan_ticks += 1
        if self.scan_ticks >= 30:
            self.scan_timer.stop()
        self.update()

    def set_frame(self, frame: np.ndarray):
        """Pushes an OpenCV BGR frame to the OpenGL rendering queue."""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        # Convert BGR (OpenCV standard) to RGB (Qt standard)
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Store as QImage
        self.image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        
        # Trigger scan animation if going from standby (offline) to live feed
        if self.scan_ticks == -1:
            self.scan_ticks = 0
            self.scan_timer.start(50) # 50ms * 30 ticks = 1.5s duration
            
        self.update()

    def clear_canvas(self):
        """Resets the canvas image to blank."""
        self.image = None
        self.scan_ticks = -1
        self.scan_timer.stop()
        self.update()

    def trigger_flash(self):
        """Triggers a bright white camera shutter flash animation overlay."""
        self.flash_alpha = 180
        if self.flash_timer_obj is not None:
            self.flash_timer_obj.stop()
        self.flash_timer_obj = QTimer(self)
        self.flash_timer_obj.timeout.connect(self.update_flash)
        self.flash_timer_obj.start(30) # 30ms updates
        self.update()

    def update_flash(self):
        self.flash_alpha -= 25
        if self.flash_alpha <= 0:
            self.flash_alpha = 0
            if self.flash_timer_obj:
                self.flash_timer_obj.stop()
                self.flash_timer_obj = None
        self.update()

    def paintEvent(self, event):
        """Renders the QImage using QPainter onto the OpenGL Widget GPU buffer."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Fill background with pure obsidian surface
        painter.fillRect(self.rect(), QColor("#020617"))
        
        if self.image is not None and not self.image.isNull():
            # Preserving strict aspect ratio
            img_width = self.image.width()
            img_height = self.image.height()
            
            widget_width = self.width()
            widget_height = self.height()
            
            aspect_ratio = img_width / img_height
            widget_aspect = widget_width / widget_height
            
            if widget_aspect > aspect_ratio:
                new_height = widget_height
                new_width = int(new_height * aspect_ratio)
                x = (widget_width - new_width) // 2
                y = 0
            else:
                new_width = widget_width
                new_height = int(new_width / aspect_ratio)
                x = 0
                y = (widget_height - new_height) // 2
                
            target_rect = QRect(x, y, new_width, new_height)
            self.target_rect = target_rect  # Cache for mouse coordinate mapping
            painter.drawImage(target_rect, self.image)
            
            # HUD overlay frame design
            painter.setPen(QColor("rgba(0, 229, 255, 0.4)"))
            painter.drawRect(target_rect)
            
            # ================= DRAW CAMERA SCANNING HUD OVERLAY =================
            if 0 <= self.scan_ticks < 30:
                t = self.scan_ticks / 30.0
                
                # 1. Subtle grid overlay inside target_rect
                painter.setPen(QPen(QColor(0, 229, 255, 18), 1))
                cols = 8
                rows = 6
                for col in range(1, cols):
                    gx = x + int(new_width * (col / cols))
                    painter.drawLine(gx, y, gx, y + new_height)
                for row in range(1, rows):
                    gy = y + int(new_height * (row / rows))
                    painter.drawLine(x, gy, x + new_width, gy)
                    
                # 2. Camera Corner Brackets (Focus points)
                bracket_len = min(25, int(new_width * 0.05))
                painter.setPen(QPen(QColor(0, 229, 255, 180), 2))
                
                # Top Left
                painter.drawLine(x + 10, y + 10, x + 10 + bracket_len, y + 10)
                painter.drawLine(x + 10, y + 10, x + 10, y + 10 + bracket_len)
                # Top Right
                painter.drawLine(x + new_width - 10, y + 10, x + new_width - 10 - bracket_len, y + 10)
                painter.drawLine(x + new_width - 10, y + 10, x + new_width - 10, y + 10 + bracket_len)
                # Bottom Left
                painter.drawLine(x + 10, y + new_height - 10, x + 10 + bracket_len, y + new_height - 10)
                painter.drawLine(x + 10, y + new_height - 10, x + 10, y + new_height - 10 - bracket_len)
                # Bottom Right
                painter.drawLine(x + new_width - 10, y + new_height - 10, x + new_width - 10 - bracket_len, y + new_height - 10)
                painter.drawLine(x + new_width - 10, y + new_height - 10, x + new_width - 10, y + new_height - 10 - bracket_len)
                
                # 3. Horizontal laser scan sweep line
                sweep_y = y + int(new_height * t)
                painter.setPen(QPen(QColor(0, 229, 255, 210), 1.5))
                painter.drawLine(x, sweep_y, x + new_width, sweep_y)
                
                # Laser scan line glow
                painter.fillRect(QRect(x, sweep_y - 2, new_width, 4), QColor(0, 229, 255, 40))
                
                # 4. Cybernetic Blinking HUD text
                if (self.scan_ticks // 3) % 2 == 0:
                    painter.setPen(QColor(0, 229, 255, 220))
                    font = QFont("Courier New", 10, QFont.Weight.Bold)
                    painter.setFont(font)
                    painter.drawText(
                        QRect(x + 20, y + new_height - 35, new_width - 40, 25),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        "NEXUS AI // SENSORS LOCKING - ENVIRONMENT TARGETING ACTIVE"
                    )
            
            # Draw camera flash overlay
            if self.flash_alpha > 0:
                painter.fillRect(target_rect, QColor(255, 255, 255, self.flash_alpha))
        else:
            # Draw Offline HUD Text
            painter.setPen(QColor("#475569"))
            painter.setFont(self.font())
            font = painter.font()
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "NEXUS CORE OFFLINE - STANDBY")
            
        painter.end()

    # ================= MOUSE FALLBACK DRAWING EVENTS =================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.image is not None:
            pos = event.position()
            mx, my = pos.x(), pos.y()
            if hasattr(self, "target_rect") and self.target_rect.contains(int(mx), int(my)):
                # Map widget coordinates to image coordinates
                rx = (mx - self.target_rect.x()) / self.target_rect.width()
                ry = (my - self.target_rect.y()) / self.target_rect.height()
                fx = int(rx * self.image.width())
                fy = int(ry * self.image.height())
                
                if self.engine is not None:
                    self.engine.writing_mode = True
                    with self.engine.canvas_lock:
                        self.engine.current_path = [(fx, fy)]
                    self.update()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.image is not None:
            pos = event.position()
            mx, my = pos.x(), pos.y()
            if hasattr(self, "target_rect") and self.target_rect.contains(int(mx), int(my)):
                # Map widget coordinates to image coordinates
                rx = (mx - self.target_rect.x()) / self.target_rect.width()
                ry = (my - self.target_rect.y()) / self.target_rect.height()
                fx = int(rx * self.image.width())
                fy = int(ry * self.image.height())
                
                if self.engine is not None:
                    if self.engine.writing_mode:
                        with self.engine.canvas_lock:
                            self.engine.current_path.append((fx, fy))
                        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.engine is not None:
                self.engine.writing_mode = False
                with self.engine.canvas_lock:
                    if self.engine.current_path:
                        self.engine.draw_paths.append(self.engine.current_path)
                        self.engine.current_path = []
                self.update()
