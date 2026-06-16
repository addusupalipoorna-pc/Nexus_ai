import sys
import os
import random
import math
from datetime import datetime
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QLabel, QFrame, QStackedWidget, QSizePolicy, QScrollArea, QTextEdit,
    QLineEdit, QDialog
)
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSlot, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer, QRect, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient, QLinearGradient, QBrush, QPainterPath, QTransform

from ui.video_canvas import VideoCanvas
from ui.analytics_hub import AnalyticsHub
from ui.settings_pane import SettingsPane
from core.engine import InferenceEngine
from database.logger import DatabaseLogger
from ui.boot_screen import BootScreen

class AnimatedLabel(QLabel):
    def __init__(self, prefix, suffix="", is_float=False, parent=None):
        super().__init__(parent)
        self.prefix = prefix
        self.suffix = suffix
        self.is_float = is_float
        self.current_val = 0.0
        self.target_val = 0.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_value)
        self.timer.start(30)
        
    def setValue(self, val):
        self.target_val = float(val)
        
    def update_value(self):
        diff = self.target_val - self.current_val
        if abs(diff) < 0.05:
            self.current_val = self.target_val
        else:
            self.current_val += diff * 0.15
            
        if self.is_float:
            self.setText(f"{self.prefix}{self.current_val:.1f}{self.suffix}")
        else:
            self.setText(f"{self.prefix}{int(round(self.current_val))}{self.suffix}")


class OnboardingDialog(QDialog):
    """Futuristic glassmorphism modal guiding first-time users on system operation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(500, 380)
        self.init_ui()
        
    def init_ui(self):
        main_lay = QVBoxLayout()
        main_lay.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame()
        container.setObjectName("container")
        container.setStyleSheet("""
            QFrame#container {
                background-color: #0E131F;
                border: 2px solid #00E5FF;
                border-radius: 8px;
            }
            QLabel {
                color: #cbd5e1;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: rgba(30, 41, 59, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: white;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 1px solid #00E5FF;
                color: #00E5FF;
            }
            QPushButton#btn_close {
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid #EF4444;
                color: #EF4444;
            }
            QPushButton#btn_close:hover {
                background-color: #EF4444;
                color: #0B0F19;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        title = QLabel("NEXUS CORE OPERATOR TUTORIAL")
        title.setStyleSheet("color: #00E5FF; font-size: 15px; font-weight: bold; letter-spacing: 1.5px;")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.pages = QStackedWidget()
        
        # Slide 1: Welcome
        p1 = QWidget()
        l1 = QVBoxLayout()
        l1.setSpacing(10)
        t1 = QLabel("Welcome to the NEXUS AI Operator Console.\n\n"
                    "This system performs deep visual intelligence extraction, multi-object tracking, "
                    "facial recognition matching, and behavioral event logging in real time.")
        t1.setWordWrap(True)
        t1.setStyleSheet("font-size: 13px; line-height: 1.4;")
        l1.addWidget(t1)
        p1.setLayout(l1)
        self.pages.addWidget(p1)
        
        # Slide 2: Surveillance View
        p2 = QWidget()
        l2 = QVBoxLayout()
        l2.setSpacing(10)
        t2 = QLabel("1. LIVE SURVEILLANCE:\n"
                    "- Start Core: Runs the multi-threaded YOLO11 capture engine.\n"
                    "- Quick Actions: Instantly overlay density heatmaps, tile the 2x2 multi-camera wall, wipe hand drawing canvases, or fire local buzzer alerts.\n"
                    "- Events HUD: Logs violations like intrusion, loitering, and running.")
        t2.setWordWrap(True)
        t2.setStyleSheet("font-size: 12px; line-height: 1.4;")
        l2.addWidget(t2)
        p2.setLayout(l2)
        self.pages.addWidget(p2)
        
        # Slide 3: Settings
        p3 = QWidget()
        l3 = QVBoxLayout()
        l3.setSpacing(10)
        t3 = QLabel("2. CORE SETTINGS:\n"
                    "- Change Stream Sources: Toggle between simulated targets, local USB webcams, mp4 files, or RTSP streams.\n"
                    "- Set Thresholds: Slide minimum YOLO detection confidence levels.\n"
                    "- Configure Alerting: Enter SMTP email keys or Telegram Bot credentials for offsite notification forwarding.")
        t3.setWordWrap(True)
        t3.setStyleSheet("font-size: 12px; line-height: 1.4;")
        l3.addWidget(t3)
        p3.setLayout(l3)
        self.pages.addWidget(p3)
        
        # Slide 4: Console
        p4 = QWidget()
        l4 = QVBoxLayout()
        l4.setSpacing(10)
        t4 = QLabel("3. HUD COMMAND CONSOLE:\n"
                    "- Located at the bottom of the sidebar, you can type shortcuts to drive the interface instantly:\n"
                    "  - 'show analytics' / 'show surveillance'\n"
                    "  - 'start' / 'stop'\n"
                    "  - 'record' / 'screenshot'\n"
                    "- Analytics Hub: Track latency plots and export HTML Executive reports.")
        t4.setWordWrap(True)
        t4.setStyleSheet("font-size: 12px; line-height: 1.4;")
        l4.addWidget(t4)
        p4.setLayout(l4)
        self.pages.addWidget(p4)
        
        layout.addWidget(self.pages, 1)
        
        self.ind_lbl = QLabel("Step 1 of 4")
        self.ind_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(self.ind_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        
        btn_lay = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self.prev_page)
        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.next_page)
        
        self.btn_close = QPushButton("Skip Tutorial")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.clicked.connect(self.accept)
        
        btn_lay.addWidget(self.btn_back)
        btn_lay.addWidget(self.btn_next)
        btn_lay.addStretch()
        btn_lay.addWidget(self.btn_close)
        layout.addLayout(btn_lay)
        
        container.setLayout(layout)
        main_lay.addWidget(container)
        self.setLayout(main_lay)
        
    def prev_page(self):
        curr = self.pages.currentIndex()
        if curr > 0:
            self.pages.setCurrentIndex(curr - 1)
            self.update_buttons()
            
    def next_page(self):
        curr = self.pages.currentIndex()
        if curr < self.pages.count() - 1:
            self.pages.setCurrentIndex(curr + 1)
            self.update_buttons()
        else:
            self.accept()
            
    def update_buttons(self):
        curr = self.pages.currentIndex()
        total = self.pages.count()
        self.btn_back.setEnabled(curr > 0)
        self.ind_lbl.setText(f"Step {curr + 1} of {total}")
        if curr == total - 1:
            self.btn_next.setText("Finish")
            self.btn_close.setText("Done")
        else:
            self.btn_next.setText("Next")
            self.btn_close.setText("Skip Tutorial")


class BackgroundWidget(QWidget):
    """
    Premium 3D animated cybernetic backdrop.
    Features:
      - 3D rotating particle sphere with perspective projection
      - Animated perspective hexagonal grid (vanishing point)
      - Orbiting plasma energy rings
      - Floating data stream columns
      - 3D holographic globe wireframe
      - Dynamic lens flare / pulse effects
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tick = 0.0
        self._w = 0
        self._h = 0

        # (Globe data removed — globe has been replaced with energy orb)

        # ── Neural drift particles (2-D overlay) ────────────────────────────
        self.drift = []
        for _ in range(40):
            self.drift.append({
                'x': random.random(), 'y': random.random(),
                'vx': random.uniform(-0.0003, 0.0003),
                'vy': random.uniform(-0.0003, 0.0003),
                'r':  random.uniform(1.2, 2.8),
                'a':  random.randint(20, 60),
            })

        # ── Data stream columns ──────────────────────────────────────────────
        self.streams = []
        for _ in range(14):
            self.streams.append({
                'x': random.random(),
                'y': random.random(),
                'speed': random.uniform(0.0008, 0.003),
                'len':  random.randint(4, 12),
                'chars': [random.choice('01ABCDEF') for _ in range(14)],
            })

        # ── Plasma rings ─────────────────────────────────────────────────────
        self.rings = [
            {'phase': random.uniform(0, math.tau), 'speed': random.uniform(0.008, 0.022),
             'rx': random.uniform(0.12, 0.22), 'ry': random.uniform(0.06, 0.12),
             'cx': random.uniform(0.2, 0.8),   'cy': random.uniform(0.2, 0.8),
             'color': random.choice([(0,229,255),(255,0,128),(128,0,255),(0,255,128)])}
            for _ in range(5)
        ]

        # ── Pulse / lens flare ───────────────────────────────────────────────
        self.pulses = []   # {'x','y','r','max_r','alpha'}
        self._pulse_timer = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)   # ~60 FPS

    # ── internal tick ────────────────────────────────────────────────────────
    def _tick(self):
        self.tick += 0.016
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            return
        self._w, self._h = w, h

        # advance drift particles
        for p in self.drift:
            p['x'] += p['vx']; p['y'] += p['vy']
            if not (0 < p['x'] < 1): p['vx'] *= -1
            if not (0 < p['y'] < 1): p['vy'] *= -1

        # advance data streams
        for s in self.streams:
            s['y'] = (s['y'] + s['speed']) % 1.2

        # advance plasma rings
        for r in self.rings:
            r['phase'] += r['speed']

        # spawn random lens flare pulses every ~2s
        self._pulse_timer += 1
        if self._pulse_timer > 120:
            self._pulse_timer = 0
            if len(self.pulses) < 6:
                self.pulses.append({
                    'x': random.random(), 'y': random.random(),
                    'r': 0, 'max_r': random.uniform(60, 160), 'alpha': 180
                })
        # advance pulses
        alive = []
        for p in self.pulses:
            p['r'] += 2.5; p['alpha'] -= 4
            if p['alpha'] > 0:
                alive.append(p)
        self.pulses = alive

        self.update()

    # ── paint ────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        t = self.tick

        # ── 0. Deep space gradient background ───────────────────────────────
        grad = QLinearGradient(0, 0, w * 0.4, h)
        grad.setColorAt(0.0, QColor(6,  8,  18))
        grad.setColorAt(0.5, QColor(8,  12, 24))
        grad.setColorAt(1.0, QColor(4,  6,  14))
        painter.fillRect(self.rect(), QBrush(grad))

        # ── 1. Perspective hex grid ──────────────────────────────────────────
        painter.save()
        vp_x, vp_y = w * 0.5, h * 0.28   # vanishing point
        n_cols = 18
        n_rows = 12
        grid_col = QColor(0, 229, 255, 8)
        painter.setPen(QPen(grid_col, 1))
        for col in range(n_cols + 1):
            fx = col / n_cols
            # bottom x spread → vanishing point
            bx = fx * w
            painter.drawLine(QPointF(bx, h), QPointF(vp_x, vp_y))
        for row in range(n_rows + 1):
            t_frac = row / n_rows
            # perspective interpolation
            y = vp_y + (h - vp_y) * (t_frac ** 1.8)
            x_left  = vp_x + (0   - vp_x) * (t_frac ** 1.8)
            x_right = vp_x + (w   - vp_x) * (t_frac ** 1.8)
            alpha_val = int(6 + 12 * t_frac)
            painter.setPen(QPen(QColor(0, 229, 255, alpha_val), 1))
            painter.drawLine(QPointF(x_left, y), QPointF(x_right, y))
        painter.restore()

        # ── 2. Central holographic energy orb (replaces globe) ────────────────
        orb_cx, orb_cy = w * 0.82, h * 0.38
        orb_r = min(w, h) * 0.08
        orb_pulse = 0.85 + 0.15 * math.sin(t * 2.0)
        # Glow halo
        orb_grad = QRadialGradient(orb_cx, orb_cy, orb_r * 3)
        orb_grad.setColorAt(0.0, QColor(0, 229, 255, int(30 * orb_pulse)))
        orb_grad.setColorAt(0.4, QColor(0, 100, 200, int(12 * orb_pulse)))
        orb_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(orb_grad))
        painter.drawEllipse(QPointF(orb_cx, orb_cy), orb_r * 3, orb_r * 3)
        # Concentric rings
        for rm, ra in [(1.0, 50), (1.4, 30), (1.8, 15)]:
            painter.setPen(QPen(QColor(0, 229, 255, ra), 0.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(orb_cx, orb_cy), orb_r * rm * orb_pulse, orb_r * rm * orb_pulse)
        # Core dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 229, 255, int(180 * orb_pulse)))
        painter.drawEllipse(QPointF(orb_cx, orb_cy), orb_r * 0.3, orb_r * 0.3)

        # ── 3. Orbiting plasma energy rings ─────────────────────────────────
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        for ring in self.rings:
            phase = ring['phase']
            rcx = ring['cx'] * w
            rcy = ring['cy'] * h
            rx  = ring['rx'] * w
            ry  = ring['ry'] * h
            # draw 3 dots orbiting an elliptical path
            rc, gc, bc = ring['color']
            for dot_i in range(3):
                angle = phase + dot_i * (math.tau / 3)
                dx = rcx + rx * math.cos(angle)
                dy = rcy + ry * math.sin(angle)
                for radius, alpha in [(8, 12), (4, 40), (2, 120)]:
                    painter.setBrush(QColor(rc, gc, bc, alpha))
                    painter.drawEllipse(QPointF(dx, dy), radius, radius)
            # draw faint elliptical orbit path
            painter.setPen(QPen(QColor(rc, gc, bc, 14), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(rcx - rx, rcy - ry, rx * 2, ry * 2))
            painter.setPen(Qt.PenStyle.NoPen)
        painter.restore()

        # ── 4. Neural drift particles + connections ──────────────────────────
        painter.save()
        drift_pts = [(int(p['x'] * w), int(p['y'] * h)) for p in self.drift]
        for i, p1 in enumerate(self.drift):
            for j in range(i + 1, len(self.drift)):
                p2 = self.drift[j]
                dist = math.hypot((p1['x'] - p2['x']) * w, (p1['y'] - p2['y']) * h)
                if dist < 110:
                    al = int(20 * (1 - dist / 110))
                    painter.setPen(QPen(QColor(0, 229, 255, al), 1))
                    painter.drawLine(drift_pts[i][0], drift_pts[i][1],
                                     drift_pts[j][0], drift_pts[j][1])
        painter.setPen(Qt.PenStyle.NoPen)
        for idx, p in enumerate(self.drift):
            painter.setBrush(QColor(0, 229, 255, p['a']))
            painter.drawEllipse(QPointF(drift_pts[idx][0], drift_pts[idx][1]),
                                p['r'], p['r'])
        painter.restore()

        # ── 5. Floating data-stream columns ─────────────────────────────────
        painter.save()
        font = QFont("Courier New", 7, QFont.Weight.Bold)
        painter.setFont(font)
        for s in self.streams:
            sx = int(s['x'] * w)
            for k, ch in enumerate(s['chars']):
                sy = int((s['y'] - k * 0.018) * h)
                if sy < 0 or sy > h:
                    continue
                fade = 1.0 - k / len(s['chars'])
                alpha = int(160 * fade)
                painter.setPen(QColor(0, 255, 128, alpha))
                painter.drawText(sx, sy, ch)
        painter.restore()

        # ── 6. Animated radar sweep line ─────────────────────────────────────
        sweep_x = int((t * 80) % w)
        trail_grad = QLinearGradient(sweep_x - 40, 0, sweep_x, 0)
        trail_grad.setColorAt(0.0, QColor(0, 229, 255, 0))
        trail_grad.setColorAt(1.0, QColor(0, 229, 255, 22))
        painter.fillRect(QRect(max(0, sweep_x - 40), 0, 40, h), QBrush(trail_grad))
        painter.setPen(QPen(QColor(0, 229, 255, 35), 1))
        painter.drawLine(sweep_x, 0, sweep_x, h)

        # ── 7. Lens flare pulses ─────────────────────────────────────────────
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.pulses:
            px, py = int(p['x'] * w), int(p['y'] * h)
            al = max(0, p['alpha'])
            grad = QRadialGradient(px, py, p['r'])
            grad.setColorAt(0.0, QColor(255, 255, 255, min(255, al)))
            grad.setColorAt(0.5, QColor(0, 229, 255, al // 2))
            grad.setColorAt(1.0, QColor(0, 229, 255, 0))
            painter.setBrush(QBrush(grad))
            r = int(p['r'])
            painter.drawEllipse(QPointF(px, py), r, r)
        painter.restore()

        # ── 8. Corner HUD brackets ───────────────────────────────────────────
        blen = 18
        painter.setPen(QPen(QColor(0, 229, 255, 55), 1))
        # top-left
        painter.drawLine(4, 4, 4 + blen, 4);  painter.drawLine(4, 4, 4, 4 + blen)
        # top-right
        painter.drawLine(w - 4, 4, w - 4 - blen, 4); painter.drawLine(w - 4, 4, w - 4, 4 + blen)
        # bottom-left
        painter.drawLine(4, h - 4, 4 + blen, h - 4); painter.drawLine(4, h - 4, 4, h - 4 - blen)
        # bottom-right
        painter.drawLine(w - 4, h - 4, w - 4 - blen, h - 4); painter.drawLine(w - 4, h - 4, w - 4, h - 4 - blen)

        painter.end()
class GlowingHexagonLogo(QWidget):
    """
    Futuristic Neural Mesh "N" constellation design logo matching the NEXUS AI storyboard.
    Features:
      - Neural network mesh layout representing "N"
      - Pulse scale animation and radial core glow
      - Reticle rings with crosshairs
      - Dual orbiting nodes on tilted elliptical paths
      - Custom radar beacon sweep wave
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 100)
        self.tick = 0.0
        rng = random.Random(7)
        self._particles = []
        for _ in range(5):
            self._particles.append({
                'angle': rng.uniform(0, math.tau),
                'speed': rng.uniform(0.5, 1.5),
                'r_mult': rng.uniform(1.2, 1.5),
                'size': rng.uniform(1.5, 2.8),
                'color': rng.choice([(0,229,255), (0,255,180), (167,139,250)]),
            })
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(25)

    def _tick(self):
        self.tick += 0.025
        self.update()

    @staticmethod
    def _hex_pts(cx, cy, r, angle_off=0):
        """Generate 6 hexagon vertices."""
        return [QPointF(cx + r * math.cos(math.tau * i / 6 + angle_off - math.pi/6),
                        cy + r * math.sin(math.tau * i / 6 + angle_off - math.pi/6))
                for i in range(6)]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx = 40
        cy = h // 2 + 4
        r = 22.0
        pulse = 0.90 + 0.10 * math.sin(self.tick * 2.5)
        R = r * pulse
        fade = 1.0
        t = self.tick

        # ── 0. Radial background energy glow ────────────────────────────────
        energy = QRadialGradient(cx, cy, R * 2.2)
        energy.setColorAt(0.0, QColor(0, 229, 255, 70))
        energy.setColorAt(0.4, QColor(0, 140, 255, 25))
        energy.setColorAt(0.7, QColor(100, 0, 255, 8))
        energy.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(energy))
        p.drawEllipse(QPointF(cx, cy), R * 2.2, R * 2.2)

        # ── 1. Outer target reticle ring (multi-pass glow) ──────────────────
        reticle_r = R * 1.1
        for thick, al in [(4, 20), (2, 60), (1, 180)]:
            p.setPen(QPen(QColor(0, 229, 255, al), thick))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), reticle_r, reticle_r)

        # Crosshair bracket ticks on the reticle ring
        tick_len = R * 0.15
        p.setPen(QPen(QColor(0, 229, 255, 200), 1.5))
        for angle_deg in [0, 90, 180, 270]:
            rad = math.radians(angle_deg)
            p.drawLine(
                QPointF(cx + reticle_r * math.cos(rad), cy + reticle_r * math.sin(rad)),
                QPointF(cx + (reticle_r - tick_len) * math.cos(rad), cy + (reticle_r - tick_len) * math.sin(rad))
            )

        # ── 2. Orbiting data ring lanes (ellipses) ──────────────────────────
        p.save()
        p.translate(cx, cy)
        orbit_r1 = R * 1.25
        orbit_r2 = R * 0.4
        
        # Orbit 1 (35 degrees tilt)
        p.rotate(35)
        p.setPen(QPen(QColor(0, 229, 255, 40), 1, Qt.PenStyle.DashLine))
        p.drawEllipse(QPointF(0, 0), orbit_r1, orbit_r2)
        # Orbiting node 1
        node1_a = t * 2.0
        n1_x = orbit_r1 * math.cos(node1_a)
        n1_y = orbit_r2 * math.sin(node1_a)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 255, 180, 240))
        p.drawEllipse(QPointF(n1_x, n1_y), 3.0, 3.0)
        p.setBrush(QColor(0, 255, 180, 70))
        p.drawEllipse(QPointF(n1_x, n1_y), 7.0, 7.0)
        
        # Orbit 2 (-35 degrees tilt)
        p.rotate(-70)
        p.setPen(QPen(QColor(0, 229, 255, 40), 1, Qt.PenStyle.DashLine))
        p.drawEllipse(QPointF(0, 0), orbit_r1, orbit_r2)
        # Orbiting node 2
        node2_a = -t * 2.4 + 1.5
        n2_x = orbit_r1 * math.cos(node2_a)
        n2_y = orbit_r2 * math.sin(node2_a)
        p.setBrush(QColor(0, 229, 255, 240))
        p.drawEllipse(QPointF(n2_x, n2_y), 3.0, 3.0)
        p.setBrush(QColor(0, 229, 255, 70))
        p.drawEllipse(QPointF(n2_x, n2_y), 7.0, 7.0)
        p.restore()

        # ── 3. Core glowing shield block background ─────────────────────────
        core_r = R * 0.72
        core_path = QPainterPath()
        core_pts = [
            QPointF(cx + core_r * math.cos(math.tau * i / 6 - math.pi/6),
                    cy + core_r * math.sin(math.tau * i / 6 - math.pi/6))
            for i in range(6)
        ]
        core_path.moveTo(core_pts[0])
        for pt in core_pts[1:]:
            core_path.lineTo(pt)
        core_path.closeSubpath()
        p.setPen(QPen(QColor(0, 229, 255, 90), 1))
        p.setBrush(QColor(6, 14, 28, 230))
        p.drawPath(core_path)

        # ── 4. Stylized glowing neural mesh "N" ─────────────────────────────
        nr = core_r * 0.65
        v_a = QPointF(cx - nr * 0.55, cy - nr * 0.72)
        v_b = QPointF(cx - nr * 0.55, cy + nr * 0.72)
        v_c = QPointF(cx + nr * 0.55, cy - nr * 0.72)
        v_d = QPointF(cx + nr * 0.55, cy + nr * 0.72)

        p.setBrush(Qt.BrushStyle.NoBrush)
        for thick, al in [(5, 35), (2.5, 90), (1.2, 255)]:
            p.setPen(QPen(QColor(0, 229, 255, al), thick, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawLine(v_a, v_b)
            p.drawLine(v_c, v_d)
            p.drawLine(v_a, v_d)
            
        p.setPen(QPen(QColor(255, 255, 255, 255), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(v_a, v_b)
        p.drawLine(v_c, v_d)
        p.drawLine(v_a, v_d)

        for pt in [v_a, v_b, v_c, v_d]:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 229, 255, 150))
            p.drawEllipse(pt, 4.0, 4.0)
            p.setBrush(QColor(255, 255, 255, 255))
            p.drawEllipse(pt, 1.8, 1.8)

        # ── 5. Expanding radar beacon wave ──────────────────────────────────
        expand_cycle = (t * 0.8) % 1.0
        expand_r = R * (1.1 + 0.65 * expand_cycle)
        expand_a = int(140 * (1.0 - expand_cycle))
        p.setPen(QPen(QColor(0, 229, 255, expand_a), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), expand_r, expand_r)

        # ── 6. Text labels ──────────────────────────────────────────────────
        font_title = QFont("Segoe UI", 11, QFont.Weight.Bold)
        font_title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        p.setFont(font_title)
        # Glow shadow
        p.setPen(QColor(0, 229, 255, 50))
        p.drawText(cx + 36, cy - 1, "NEXUS AI")
        # Bright text
        p.setPen(QColor(0, 229, 255, 255))
        p.drawText(cx + 35, cy - 2, "NEXUS AI")

        font_sub = QFont("Segoe UI", 7, QFont.Weight.Bold)
        font_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        p.setFont(font_sub)
        p.setPen(QColor(120, 140, 170))
        p.drawText(cx + 36, cy + 12, "SURVEILLANCE SYSTEM")

        p.end()





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
        
        # Help Button
        self.btn_help = QPushButton("?")
        self.btn_help.setObjectName("btn_help")
        self.btn_help.setToolTip("Launch interactive onboarding tour")
        self.btn_help.setStyleSheet("QPushButton { color: #00E5FF; font-size: 14px; font-weight: bold; }")
        self.btn_help.clicked.connect(self.parent_win.show_onboarding_tutorial)
        layout.addWidget(self.btn_help)
        
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
        self.canvas.engine = self.engine
        self.view_analytics = AnalyticsHub(self.db.get_db_path())
        self.view_settings = SettingsPane()
        self.view_boot = BootScreen()

        # Detection cache
        self.tracked_ids_cache = set()

        self.init_ui()
        self.connect_signals()

        # Auto-start core engine if in no-auth/testing mode
        if "--no-auth" in sys.argv:
            self.start_core()

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

        # Main Area (Sidebar + QStackedWidget) using custom BackgroundWidget
        main_content = BackgroundWidget()
        main_content.setObjectName("main_content")
        main_content_layout = QHBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        main_content.setLayout(main_content_layout)
        shell_layout.addWidget(main_content)

        # ================= SIDEBAR NAVIGATOR =================
        self.sidebar_widget = QFrame()
        self.sidebar_widget.setObjectName("sidebar")
        self.sidebar_widget.setFixedWidth(200)
        self.sidebar_widget.setStyleSheet("""
            QFrame#sidebar {
                background-color: rgba(14, 19, 31, 0.7);
                border-right: 1px solid rgba(255, 255, 255, 0.05);
            }
            QLabel#nav_header {
                font-size: 16px;
                font-weight: bold;
                color: #00E5FF;
                letter-spacing: 2px;
                padding: 20px 15px 5px 15px;
                background-color: transparent;
            }
            QLabel#nav_subheader {
                font-size: 9px;
                color: #64748b;
                letter-spacing: 1px;
                padding: 0px 15px 25px 15px;
                background-color: transparent;
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
        
        # Header (Animated Glowing Hexagon Logo)
        self.logo_widget = GlowingHexagonLogo()
        sidebar_layout.addWidget(self.logo_widget)

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

        # HUD Command Console / Voice Assistant Mock
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("SYS COMMAND...")
        self.cmd_input.setToolTip("Type console shortcuts (e.g. 'show analytics', 'record')")
        self.cmd_input.setStyleSheet("""
            QLineEdit {
                background-color: #020617;
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: #00E5FF;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 6px;
                margin: 10px;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #00E5FF;
            }
        """)
        self.cmd_input.returnPressed.connect(self.process_console_command)
        sidebar_layout.addWidget(self.cmd_input)

        sidebar_layout.addStretch()

        # System healthy label
        self.lbl_healthy = QLabel("SYSTEM: SECURED")
        self.lbl_healthy.setStyleSheet("color: #10B981; font-size: 10px; font-weight: bold; padding: 15px; background-color: transparent;")
        sidebar_layout.addWidget(self.lbl_healthy)

        self.sidebar_widget.setLayout(sidebar_layout)
        main_content_layout.addWidget(self.sidebar_widget)

        # ================= STACKED PAGE CONTAINER =================
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent;")
        main_content_layout.addWidget(self.stacked_widget, 1)

        # Page 0: Live Surveillance Dashboard layout
        self.page_surveillance = QWidget()
        self.page_surveillance.setStyleSheet("background-color: transparent;")
        dash_layout = QHBoxLayout()
        dash_layout.setSpacing(15)
        dash_layout.setContentsMargins(15, 15, 15, 15)
        self.page_surveillance.setLayout(dash_layout)

        # Left Column: Video display Canvas + controls underneath
        video_area = QWidget()
        video_area.setStyleSheet("background-color: transparent;")
        video_layout = QVBoxLayout()
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(10)
        
        # Add our OpenGL Video canvas
        video_layout.addWidget(self.canvas, 1)
        
        # Canvas Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
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
        
        # Separator line
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.HLine)
        sep_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); max-height: 1px; margin-top: 5px; margin-bottom: 5px;")
        video_layout.addWidget(sep_line)
        
        # Quick Actions Bar Layout
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(8)
        
        self.btn_quick_heatmap = QPushButton("TOGGLE HEATMAP")
        self.btn_quick_heatmap.setEnabled(False)
        self.btn_quick_heatmap.setToolTip("Superimpose live target activity density overlays")
        self.btn_quick_heatmap.setStyleSheet("""
            QPushButton {
                background-color: rgba(192, 132, 252, 0.1);
                border: 1px solid rgba(192, 132, 252, 0.4);
                color: #C084FC;
                font-size: 10px;
                padding: 6px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(192, 132, 252, 0.25);
                border: 1px solid #C084FC;
            }
        """)
        quick_layout.addWidget(self.btn_quick_heatmap)
        
        self.btn_quick_multicam = QPushButton("TOGGLE GRID WALL")
        self.btn_quick_multicam.setEnabled(False)
        self.btn_quick_multicam.setToolTip("Tile 2x2 grid (Primary, Target simulation, Thermal, Radar sweep)")
        self.btn_quick_multicam.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 229, 255, 0.1);
                border: 1px solid rgba(0, 229, 255, 0.4);
                color: #00E5FF;
                font-size: 10px;
                padding: 6px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(0, 229, 255, 0.25);
                border: 1px solid #00E5FF;
            }
        """)
        quick_layout.addWidget(self.btn_quick_multicam)
        
        self.btn_quick_clear = QPushButton("CLEAR WRITING")
        self.btn_quick_clear.setEnabled(False)
        self.btn_quick_clear.setToolTip("Wipe MediaPipe hand writing canvas drawings")
        self.btn_quick_clear.setStyleSheet("""
            QPushButton {
                background-color: rgba(245, 158, 11, 0.1);
                border: 1px solid rgba(245, 158, 11, 0.4);
                color: #F59E0B;
                font-size: 10px;
                padding: 6px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(245, 158, 11, 0.25);
                border: 1px solid #F59E0B;
            }
        """)
        quick_layout.addWidget(self.btn_quick_clear)

        self.btn_quick_airwriting = QPushButton("✍ AIR WRITING: OFF")
        self.btn_quick_airwriting.setEnabled(False)
        self.btn_quick_airwriting.setCheckable(True)
        self.btn_quick_airwriting.setChecked(False)
        self.btn_quick_airwriting.setToolTip(
            "Toggle MediaPipe hand air writing.\n"
            "☝ Index finger up = WRITE\n"
            "✌ Index + Middle up = HOVER\n"
            "🖐 Open hand = CLEAR CANVAS"
        )
        self.btn_quick_airwriting.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.08);
                border: 1px solid rgba(16, 185, 129, 0.35);
                color: #6EE7B7;
                font-size: 10px;
                padding: 6px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.2);
                border: 1px solid #10B981;
            }
            QPushButton:checked {
                background-color: rgba(16, 185, 129, 0.35);
                border: 2px solid #10B981;
                color: #ffffff;
            }
        """)
        quick_layout.addWidget(self.btn_quick_airwriting)

        self.btn_quick_siren = QPushButton("SIREN TEST")
        self.btn_quick_siren.setEnabled(False)
        self.btn_quick_siren.setToolTip("Trigger local audible alert beep diagnostics")
        self.btn_quick_siren.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.4);
                color: #EF4444;
                font-size: 10px;
                padding: 6px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
                border: 1px solid #EF4444;
            }
        """)
        quick_layout.addWidget(self.btn_quick_siren)

        self.btn_quick_heatmap.clicked.connect(self.toggle_quick_heatmap)
        self.btn_quick_multicam.clicked.connect(self.toggle_quick_multicam)
        self.btn_quick_clear.clicked.connect(self.clear_quick_airwriting)
        self.btn_quick_airwriting.clicked.connect(self.toggle_air_writing)
        self.btn_quick_siren.clicked.connect(self.trigger_quick_siren)
        
        video_layout.addLayout(quick_layout)
        
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
        
        self.lbl_latency = AnimatedLabel("LATENCY: ", " ms", is_float=True)
        self.lbl_latency.setToolTip("Inference cycle execution time in milliseconds (camera frames capture, model predict, ByteTrack).")
        self.lbl_fps = AnimatedLabel("SYS FPS: ", is_float=True)
        self.lbl_fps.setToolTip("Surveillance feed frames processed per second.")
        self.lbl_active = AnimatedLabel("ACTIVE TRACKS: ", is_float=False)
        self.lbl_active.setToolTip("Currently tracked visual targets.")
        
        for lbl in [self.lbl_latency, self.lbl_fps, self.lbl_active]:
            lbl.setStyleSheet("color: #f8fafc; font-weight: bold; font-family: monospace; font-size: 13px;")
            telemetry_layout.addWidget(lbl)
            
        panel_layout.addLayout(telemetry_layout)

        # Threat Level Card
        threat_title = QLabel("LIVE THREAT ASSESSMENT")
        threat_title.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 5px; margin-top: 10px;")
        panel_layout.addWidget(threat_title)
        
        self.lbl_threat_level = QLabel("THREAT LEVEL: LOW")
        self.lbl_threat_level.setToolTip("Computed threat level categories derived from active risks.")
        self.lbl_threat_level.setStyleSheet("color: #10B981; font-weight: bold; font-size: 14px; font-family: monospace;")
        panel_layout.addWidget(self.lbl_threat_level)
        
        self.lbl_risk_score = QLabel("RISK SCORE: 5%")
        self.lbl_risk_score.setToolTip("Aggregate risk index calculated based on object class, counts, and violations.")
        self.lbl_risk_score.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px; font-family: monospace; margin-bottom: 10px;")
        panel_layout.addWidget(self.lbl_risk_score)

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

        # Alarm HUD Alerts list (Contextual warned style by default)
        self.alarm_header = QLabel("SECURITY EVENTS HUD")
        self.alarm_header.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 5px;")
        panel_layout.addWidget(self.alarm_header)

        self.alarm_text = QTextEdit()
        self.alarm_text.setReadOnly(True)
        self.alarm_text.setStyleSheet("""
            QTextEdit {
                background-color: #020617;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                color: #94A3B8;
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
        self.stacked_widget.addWidget(self.view_boot)

        # Initialize buttons style properties
        self._update_sidebar_styling()
        
        # Connect boot screen finished and switch to it first
        self.view_boot.finished.connect(self.handle_boot_complete)
        self.stacked_widget.setCurrentIndex(3)
        self.sidebar_widget.setFixedWidth(0)

    def connect_signals(self):
        # UI Control Actions
        self.btn_start.clicked.connect(self.start_core)
        self.btn_stop.clicked.connect(self.stop_core)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_shot.clicked.connect(self.trigger_snapshot)
        self.btn_rec.clicked.connect(self.toggle_recording)

        # Engine Signals
        self.engine.frame_ready.connect(self.handle_frame_packet)
        self.engine.telemetry_ready.connect(self.handle_telemetry_packet)
        self.engine.status_msg.connect(self.handle_status_msg)
        
        # Settings Changed
        self.view_settings.settings_changed.connect(self.engine.apply_settings)

    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        
        # Update active flags
        self.btn_dash.setProperty("active", "true" if index == 0 else "false")
        self.btn_analytics.setProperty("active", "true" if index == 1 else "false")
        self.btn_settings.setProperty("active", "true" if index == 2 else "false")
        
        self._update_sidebar_styling()
        
        # Refresh analytics / trigger chart animations
        if index == 1:
            self.view_analytics.refresh_database_grid()
            self.view_analytics.trigger_charts_animation()

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
            
            # Enable quick action controls
            self.btn_quick_heatmap.setEnabled(True)
            self.btn_quick_multicam.setEnabled(True)
            self.btn_quick_clear.setEnabled(True)
            self.btn_quick_airwriting.setEnabled(True)
            self.btn_quick_airwriting.setChecked(True)
            self.btn_quick_airwriting.setText("✍ AIR WRITING: ON")
            self.btn_quick_siren.setEnabled(True)
            
            self.lbl_healthy.setText("SYSTEM: MONITORING")
            self.lbl_healthy.setStyleSheet("color: #00E5FF; font-size: 10px; font-weight: bold; padding: 15px; background-color: transparent;")
            
            time_str = datetime.now().strftime("%H:%M:%S")
            self.alarm_text.append(f"[{time_str}] [HUD] SURVEILLANCE CORE INITIALIZED & RUNNING")

    def stop_core(self):
        """Shuts down QThread inference engine safely."""
        if self.engine.isRunning():
            self.lbl_healthy.setText("SYSTEM: STANDBY")
            self.lbl_healthy.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; padding: 15px; background-color: transparent;")
            
            # Request stop and join
            self.engine.is_running = False
            self.engine.wait()
            
            # Reset Controls
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_rec.setEnabled(False)
            self.btn_shot.setEnabled(False)
            
            # Disable quick actions
            self.btn_quick_heatmap.setEnabled(False)
            self.btn_quick_multicam.setEnabled(False)
            self.btn_quick_clear.setEnabled(False)
            self.btn_quick_airwriting.setEnabled(False)
            self.btn_quick_airwriting.setChecked(False)
            self.btn_quick_airwriting.setText("✍ AIR WRITING: OFF")
            self.btn_quick_siren.setEnabled(False)
            
            self.btn_pause.setText("PAUSE")
            
            # Stop recording if active
            self.engine.stop_recording()
            self.btn_rec.setText("RECORD MP4")
            self.btn_rec.setProperty("recording", "false")
            self.btn_rec.style().unpolish(self.btn_rec)
            self.btn_rec.style().polish(self.btn_rec)
            
            self.canvas.clear_canvas()
            
            # Update labels
            self.lbl_latency.setValue(0.0)
            self.lbl_fps.setValue(0.0)
            self.lbl_active.setValue(0)
            
            # Reset warning style
            self.update_warning_states(False)
            
            # Clear counts list
            for i in reversed(range(self.counts_list_layout.count())): 
                self.counts_list_layout.itemAt(i).widget().setParent(None)
                
            time_str = datetime.now().strftime("%H:%M:%S")
            self.alarm_text.append(f"[{time_str}] [HUD] SURVEILLANCE CORE HALTED - FEED OFFLINE")

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
            time_str = datetime.now().strftime("%H:%M:%S")
            if is_rec:
                self.engine.start_recording()
                self.btn_rec.setText("STOP RECORD")
                self.btn_rec.setProperty("recording", "true")
                self.alarm_text.append(f"[{time_str}] [HUD] MP4 RECORDING INITIALIZED")
            else:
                self.engine.stop_recording()
                self.btn_rec.setText("RECORD MP4")
                self.btn_rec.setProperty("recording", "false")
                self.alarm_text.append(f"[{time_str}] [HUD] MP4 RECORDING TERMINATED")
                
            self.btn_rec.style().unpolish(self.btn_rec)
            self.btn_rec.style().polish(self.btn_rec)

    def trigger_snapshot(self):
        if self.engine.isRunning():
            self.engine.trigger_screenshot("annotated")
            self.canvas.trigger_flash()  # Shutter flash animation overlay
            time_str = datetime.now().strftime("%H:%M:%S")
            self.alarm_text.append(f"[{time_str}] [HUD] SNAPSHOT CAPTURE COMMAND SENT")

    # ================= QUICK ACTION SLOTS =================
    def toggle_quick_heatmap(self):
        self.engine.show_heatmap = not self.engine.show_heatmap
        self.view_settings.cb_heatmap.setChecked(self.engine.show_heatmap)
        status_str = "ACTIVE" if self.engine.show_heatmap else "STANDBY"
        time_str = datetime.now().strftime("%H:%M:%S")
        self.alarm_text.append(f"[{time_str}] [HUD] QUICK TOGGLE HEATMAP: {status_str}")

    def toggle_quick_multicam(self):
        self.engine.multi_camera_mode = not self.engine.multi_camera_mode
        self.view_settings.cb_multicam.setChecked(self.engine.multi_camera_mode)
        status_str = "GRID COMPOSITOR ON" if self.engine.multi_camera_mode else "SINGLE CAM GRID OFF"
        time_str = datetime.now().strftime("%H:%M:%S")
        self.alarm_text.append(f"[{time_str}] [HUD] QUICK TOGGLE GRID WALL: {status_str}")

    def clear_quick_airwriting(self):
        with self.engine.canvas_lock:
            self.engine.draw_paths = []
            self.engine.current_path = []
        time_str = datetime.now().strftime("%H:%M:%S")
        self.alarm_text.append(f"[{time_str}] [HUD] AIR WRITING DRAW PATHS WIPED")

    def toggle_air_writing(self):
        """Toggles MediaPipe hand air-writing on/off."""
        enabled = self.btn_quick_airwriting.isChecked()
        self.engine.air_writing_enabled = enabled
        time_str = datetime.now().strftime("%H:%M:%S")
        if enabled:
            self.btn_quick_airwriting.setText("\u270d AIR WRITING: ON")
            self.alarm_text.append(
                f"[{time_str}] [HUD] AIR WRITING ENABLED  "
                f"| \u261d INDEX UP=WRITE  \u270c INDEX+MID=HOVER  \ud83d\udd90 OPEN HAND=CLEAR"
            )
        else:
            self.btn_quick_airwriting.setText("\u270d AIR WRITING: OFF")
            # Clear canvas when disabling so stale strokes don't persist
            with self.engine.canvas_lock:
                self.engine.draw_paths = []
                self.engine.current_path = []
            self.alarm_text.append(f"[{time_str}] [HUD] AIR WRITING DISABLED")

    def trigger_quick_siren(self):
        time_str = datetime.now().strftime("%H:%M:%S")
        self.alarm_text.append(f"[{time_str}] [HUD] TARGET AUDIBLE SIREN DIAGNOSTIC TEST FIRED")
        self.engine._trigger_audio_beep()
        
        # Visual alarm feedback: flash HUD warning states red for 1.0 second
        self.update_warning_states(True)
        QTimer.singleShot(1000, lambda: self.update_warning_states(False))

    def update_warning_states(self, alarm_active):
        """Changes HUD borders and text labels colors dynamically depending on alerts."""
        if alarm_active:
            # Active violation -> flash neon red
            self.alarm_text.setStyleSheet("""
                QTextEdit {
                    background-color: #0F0206;
                    border: 1.5px solid #FF003C;
                    border-radius: 4px;
                    color: #FF003C;
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                }
            """)
            self.alarm_header.setStyleSheet("color: #FF003C; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1.5px solid #FF003C; padding-bottom: 5px;")
        else:
            # Standby/secured -> cool slate grey
            self.alarm_text.setStyleSheet("""
                QTextEdit {
                    background-color: #020617;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 4px;
                    color: #94A3B8;
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                }
            """)
            self.alarm_header.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 5px;")

    def handle_status_msg(self, msg):
        """Appends engine status messages directly to the Security Events HUD."""
        time_str = datetime.now().strftime("%H:%M:%S")
        self.alarm_text.append(f"[{time_str}] [SYS] {msg.upper()}")

    @pyqtSlot(object, dict)
    def handle_frame_packet(self, frame, payload):
        """Processes signals containing painted frame array and HUD metadata dictionary."""
        # Update OpenGL painting canvas
        self.canvas.set_frame(frame)
        
        # Update telemetry labels
        active_objects = payload["active_objects"]
        self.lbl_active.setValue(len(active_objects))

        # Compute dynamic threat score
        risk_score = 5
        intrusion_count = 0
        loitering_count = 0
        running_count = 0
        
        for obj_id, info in active_objects.items():
            risk_score += 2 # 2% per object
            if info.get("intrusion"):
                risk_score += 25
                intrusion_count += 1
            if info.get("behavior") == "loitering":
                risk_score += 40
                loitering_count += 1
            if info.get("behavior") == "running":
                risk_score += 30
                running_count += 1
                
        risk_score = min(100, risk_score)
        self.lbl_risk_score.setText(f"RISK SCORE: {risk_score}%")
        
        if risk_score <= 15:
            self.lbl_threat_level.setText("THREAT LEVEL: LOW")
            self.lbl_threat_level.setStyleSheet("color: #10B981; font-weight: bold; font-size: 14px; font-family: monospace;")
        elif risk_score <= 50:
            self.lbl_threat_level.setText("THREAT LEVEL: MEDIUM")
            self.lbl_threat_level.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 14px; font-family: monospace;")
        else:
            self.lbl_threat_level.setText("THREAT LEVEL: CRITICAL")
            self.lbl_threat_level.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 14px; font-family: monospace;")

        # Style shift for alerts (Contextual warnings check)
        alarm_active = payload["intrusion_alert"] or loitering_count > 0 or running_count > 0
        self.update_warning_states(alarm_active)

        # Log new objects to the event list
        current_time = datetime.now().strftime("%H:%M:%S")
        for obj_id, info in active_objects.items():
            if obj_id not in self.tracked_ids_cache:
                self.tracked_ids_cache.add(obj_id)
                self.alarm_text.append(f"[{current_time}] {info['class'].upper()} Detected (ID: {obj_id})")
        
        # Update target classification counts list
        counts = {}
        for obj_id, info in active_objects.items():
            cls_name = info["class"]
            counts[cls_name] = counts.get(cls_name, 0) + 1
            
        # Clean counts widgets
        for i in reversed(range(self.counts_list_layout.count())): 
            self.counts_list_layout.itemAt(i).widget().setParent(None)
            
        if not counts:
            lbl = QLabel("No active targets detected")
            lbl.setStyleSheet("color: #64748b; font-style: italic; background-color: transparent;")
            self.counts_list_layout.addWidget(lbl)
        else:
            for cls_name, count in counts.items():
                row = QWidget()
                row.setStyleSheet("background-color: transparent;")
                row_lay = QHBoxLayout()
                row_lay.setContentsMargins(0, 2, 0, 2)
                
                name_lbl = QLabel(cls_name.upper())
                name_lbl.setStyleSheet("color: #94a3b8; background-color: transparent;")
                val_lbl = QLabel(str(count))
                val_lbl.setStyleSheet("color: #f8fafc; font-weight: bold; background-color: transparent;")
                
                row_lay.addWidget(name_lbl)
                row_lay.addStretch()
                row_lay.addWidget(val_lbl)
                row.setLayout(row_lay)
                self.counts_list_layout.addWidget(row)
                
        # Handle Intrusion alarm violations
        if payload["intrusion_alert"]:
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
        self.lbl_latency.setValue(latency_ms)
        self.lbl_fps.setValue(fps)
        
        # Send telemetry to Analytics hub rolling charts
        self.view_analytics.feed_live_latency(latency_ms)

    def handle_boot_complete(self):
        """Fades out boot sequence and initiates sidebar transition."""
        self.stacked_widget.setCurrentIndex(0)
        self.animate_sidebar()
        self.start_core()
        
        # Onboarding Tutorial auto-run for first-time launch
        tutorial_completed_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", ".tutorial_completed")
        if not os.path.exists(tutorial_completed_file):
            QTimer.singleShot(1000, self.show_onboarding_tutorial)
            try:
                os.makedirs(os.path.dirname(tutorial_completed_file), exist_ok=True)
                with open(tutorial_completed_file, "w") as f:
                    f.write("completed")
            except Exception:
                pass


    def show_onboarding_tutorial(self):
        """Triggers the onboarding wizard tutorial overlay manually or on startup."""
        dlg = OnboardingDialog(self)
        dlg.exec()

    def animate_sidebar(self):
        """Animate sidebar sliding in from left and menu items staggered reveal."""
        self.sidebar_widget.setFixedWidth(0)
        
        self.sidebar_anim = QPropertyAnimation(self.sidebar_widget, b"minimumWidth")
        self.sidebar_anim.setDuration(500)
        self.sidebar_anim.setStartValue(0)
        self.sidebar_anim.setEndValue(200)
        self.sidebar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.sidebar_anim_max = QPropertyAnimation(self.sidebar_widget, b"maximumWidth")
        self.sidebar_anim_max.setDuration(500)
        self.sidebar_anim_max.setStartValue(0)
        self.sidebar_anim_max.setEndValue(200)
        self.sidebar_anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Create parallel animation group
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.sidebar_anim)
        self.anim_group.addAnimation(self.sidebar_anim_max)
        
        # Hide menu buttons temporarily for stagger
        self.btn_dash.hide()
        self.btn_analytics.hide()
        self.btn_settings.hide()
        
        def show_btn1(): self.btn_dash.show()
        def show_btn2(): self.btn_analytics.show()
        def show_btn3(): self.btn_settings.show()
        
        QTimer.singleShot(400, show_btn1)
        QTimer.singleShot(550, show_btn2)
        QTimer.singleShot(700, show_btn3)
        
        self.anim_group.start()

    def process_console_command(self):
        """Processes typed text commands for the voice assistant / console interface."""
        cmd = self.cmd_input.text().strip().lower()
        self.cmd_input.clear()
        
        if not cmd:
            return
            
        time_str = datetime.now().strftime("%H:%M:%S")
        
        if "analytics" in cmd or "show analytics" in cmd:
            self.switch_page(1)
            self.alarm_text.append(f"[{time_str}] [CMD] NAVIGATING TO ANALYTICS HUB")
        elif "surveillance" in cmd or "dash" in cmd or "show surveillance" in cmd:
            self.switch_page(0)
            self.alarm_text.append(f"[{time_str}] [CMD] NAVIGATING TO LIVE SURVEILLANCE")
        elif "settings" in cmd or "show settings" in cmd:
            self.switch_page(2)
            self.alarm_text.append(f"[{time_str}] [CMD] NAVIGATING TO CORE SETTINGS")
        elif "start" in cmd:
            self.start_core()
            self.alarm_text.append(f"[{time_str}] [CMD] INITIATING SURVEILLANCE ENGINE")
        elif "stop" in cmd:
            self.stop_core()
            self.alarm_text.append(f"[{time_str}] [CMD] HALTING SURVEILLANCE ENGINE")
        elif "record" in cmd or "video" in cmd:
            self.toggle_recording()
            self.alarm_text.append(f"[{time_str}] [CMD] TOGGLED MP4 VIDEO RECORDING")
        elif "screenshot" in cmd or "shot" in cmd:
            self.trigger_snapshot()
            self.alarm_text.append(f"[{time_str}] [CMD] SCREENSHOT CAPTURED SUCCESSFULLY")
        else:
            self.alarm_text.append(f"[{time_str}] [CMD] COMMAND UNRECOGNIZED: '{cmd.upper()}'")

    def closeEvent(self, event):
        """Wipes threads on window close events."""
        self.stop_core()
        event.accept()
