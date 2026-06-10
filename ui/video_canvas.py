import numpy as np
import cv2
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QPainter, QImage, QColor
from PyQt6.QtCore import Qt, QRect

class VideoCanvas(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.setStyleSheet("background-color: #020617; border: 2px solid #00E5FF; border-radius: 6px;")
        
    def initializeGL(self):
        """Initializes OpenGL context."""
        pass

    def set_frame(self, frame: np.ndarray):
        """Pushes an OpenCV BGR frame to the OpenGL rendering queue."""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        # Convert BGR (OpenCV standard) to RGB (Qt standard)
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Store as QImage
        # Note: We copy the data to avoid segment faults from GC of the numpy array
        self.image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        
        # Request redraw
        self.update()

    def clear_canvas(self):
        """Resets the canvas image to blank."""
        self.image = None
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
                # Bounded by height
                new_height = widget_height
                new_width = int(new_height * aspect_ratio)
                x = (widget_width - new_width) // 2
                y = 0
            else:
                # Bounded by width
                new_width = widget_width
                new_height = int(new_width / aspect_ratio)
                x = 0
                y = (widget_height - new_height) // 2
                
            target_rect = QRect(x, y, new_width, new_height)
            painter.drawImage(target_rect, self.image)
            
            # HUD overlay frame design
            painter.setPen(QColor("rgba(0, 229, 255, 0.4)"))
            painter.drawRect(target_rect)
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
