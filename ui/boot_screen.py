"""
NEXUS AI – Cinematic Startup Animation (High-Fidelity 3x3 Storyboard Grid)
Displays all 9 diagnostic scenes concurrently in a 3x3 grid matching the storyboard layout.
All animations play synchronously over 25 seconds, completing perfectly.
"""

import math
import random
import numpy as np

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QRect, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush,
    QLinearGradient, QRadialGradient, QPainterPath, QPixmap,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def ease_in_out(t):
    t = clamp(t, 0, 1)
    return t * t * (3 - 2 * t)

# ── Timings ──────────────────────────────────────────────────────────────────
TICK_MS   = 16          # ~60 FPS
TOTAL_SEC = 28.0        # 7 scenes * 4.0 seconds per scene


class BootScreen(QWidget):
    finished = pyqtSignal()

    # ── init ─────────────────────────────────────────────────────────────────
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setStyleSheet("background:#01040d;")
        self.setMouseTracking(True)

        self._t    = 0.0          # wall-clock seconds
        self._done = False
        self._skip_hovered = False

        # Load high-quality street scene image if available
        import os
        ui_dir = os.path.dirname(os.path.abspath(__file__))
        self.street_pixmap = QPixmap(os.path.join(ui_dir, "street_scene.png"))

        # pre-compute random scene assets once
        self._build_scene_assets()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

    # ── asset construction ───────────────────────────────────────────────────
    def _build_scene_assets(self):
        rng = random.Random(1337)

        # Scene 1 – loading bars
        self._bars = [
            {"label": "Vision Engine",     "target": 1.0},
            {"label": "Detection Models",  "target": 1.0},
            {"label": "Tracking System",   "target": 1.0},
            {"label": "Database",          "target": 1.0},
        ]

        # Scene 2 – Brain-shaped neural network nodes (Anatomical Lobe clusters)
        self._neuro_nodes = []
        node_groups = []
        
        # 1. Frontal Lobe (28 nodes) - Anterior-Superior (top-left)
        for _ in range(28):
            r = rng.uniform(0, 1)
            angle = rng.uniform(0, math.tau)
            dx = 0.14 * math.sqrt(r) * math.cos(angle)
            dy = 0.11 * math.sqrt(r) * math.sin(angle)
            self._neuro_nodes.append((0.36 + dx, 0.40 + dy))
            node_groups.append("frontal")
            
        # 2. Parietal Lobe (28 nodes) - Superior-Posterior (top-right)
        for _ in range(28):
            r = rng.uniform(0, 1)
            angle = rng.uniform(0, math.tau)
            dx = 0.12 * math.sqrt(r) * math.cos(angle)
            dy = 0.10 * math.sqrt(r) * math.sin(angle)
            self._neuro_nodes.append((0.58 + dx, 0.38 + dy))
            node_groups.append("parietal")
            
        # 3. Occipital Lobe (18 nodes) - Posterior (right-back)
        for _ in range(18):
            r = rng.uniform(0, 1)
            angle = rng.uniform(0, math.tau)
            dx = 0.08 * math.sqrt(r) * math.cos(angle)
            dy = 0.08 * math.sqrt(r) * math.sin(angle)
            self._neuro_nodes.append((0.70 + dx, 0.49 + dy))
            node_groups.append("occipital")
            
        # 4. Temporal Lobe (24 nodes) - Inferior-Anterior (mid-left bottom)
        for _ in range(24):
            r = rng.uniform(0, 1)
            angle = rng.uniform(0, math.tau)
            dx = 0.11 * math.sqrt(r) * math.cos(angle)
            dy = 0.07 * math.sqrt(r) * math.sin(angle)
            self._neuro_nodes.append((0.42 + dx, 0.54 + dy))
            node_groups.append("temporal")
            
        # 5. Cerebellum (18 nodes) - Bottom Right (horizontal layered lines)
        for _ in range(18):
            r = rng.uniform(0, 1)
            angle = rng.uniform(0, math.tau)
            dx = 0.08 * math.sqrt(r) * math.cos(angle)
            dy = 0.04 * math.sqrt(r) * math.sin(angle)
            self._neuro_nodes.append((0.62 + dx, 0.62 + dy))
            node_groups.append("cerebellum")
            
        # 6. Brainstem (12 nodes) - Vertical column at the bottom
        for _ in range(12):
            sy = rng.uniform(0.58, 0.78)
            sx = 0.51 + rng.uniform(-0.018, 0.018)
            self._neuro_nodes.append((sx, sy))
            node_groups.append("brainstem")

        self._neuro_edges = []
        for i in range(len(self._neuro_nodes)):
            for j in range(i + 1, len(self._neuro_nodes)):
                n1 = self._neuro_nodes[i]
                n2 = self._neuro_nodes[j]
                g1 = node_groups[i]
                g2 = node_groups[j]
                
                dist = math.hypot(n1[0] - n2[0], n1[1] - n2[1])
                
                if g1 == g2:
                    threshold = 0.075
                    if g1 == "cerebellum":
                        threshold = 0.09
                        if abs(n1[1] - n2[1]) > 0.02: 
                            continue
                    if dist < threshold:
                        self._neuro_edges.append((i, j))
                else:
                    # Allow inter-lobe tract connections
                    if (g1 == "frontal" and g2 == "parietal") or (g1 == "parietal" and g2 == "frontal"):
                        if dist < 0.12 and rng.random() < 0.25:
                            self._neuro_edges.append((i, j))
                    elif (g1 == "parietal" and g2 == "occipital") or (g1 == "occipital" and g2 == "parietal"):
                        if dist < 0.12 and rng.random() < 0.25:
                            self._neuro_edges.append((i, j))
                    elif (g1 == "occipital" and g2 == "cerebellum") or (g1 == "cerebellum" and g2 == "occipital"):
                        if dist < 0.10 and rng.random() < 0.2:
                            self._neuro_edges.append((i, j))
                    elif (g1 == "temporal" and g2 == "frontal") or (g1 == "frontal" and g2 == "temporal"):
                        if dist < 0.11 and rng.random() < 0.2:
                            self._neuro_edges.append((i, j))
                    elif g1 == "brainstem" or g2 == "brainstem":
                        if dist < 0.10 and rng.random() < 0.25:
                            self._neuro_edges.append((i, j))
                    # Corpus callosum / association long-range fibers
                    elif dist < 0.32 and rng.random() < 0.015:
                        self._neuro_edges.append((i, j))

        # Scene 3 – convergence particles
        self._conv_pts = []
        for _ in range(220):
            angle = rng.uniform(0, math.tau)
            dist  = rng.uniform(0.45, 0.75)
            sx = 0.5 + dist * math.cos(angle)
            sy = 0.5 + dist * math.sin(angle)
            tx = rng.uniform(0.4, 0.6)
            ty = rng.uniform(0.42, 0.58)
            self._conv_pts.append((sx, sy, tx, ty,
                                   rng.uniform(1.2, 3.2),
                                   rng.randint(90, 220)))

        # Scene 4 – globe points (lat/lon pairs) — random scatter for star dust
        self._globe_pts = [
            (rng.uniform(-math.pi/2, math.pi/2),
             rng.uniform(0, math.tau))
            for _ in range(160)
        ]
        # Continent outlines (simplified polygon lat/lon in degrees)
        self._continents = [
            # North America
            [(50,-130),(55,-120),(60,-110),(65,-100),(60,-80),(50,-65),(45,-65),(40,-75),(30,-82),(25,-82),
             (28,-98),(22,-100),(15,-90),(10,-83),(10,-78),(18,-77),(20,-88),(30,-105),(35,-120),(40,-124),(48,-126),(50,-130)],
            # South America
            [(10,-78),(5,-77),(0,-80),(-5,-80),(-10,-76),(-15,-75),(-20,-63),(-25,-58),(-30,-55),
             (-35,-58),(-40,-65),(-45,-68),(-50,-72),(-55,-68),(-50,-75),(-45,-75),(-35,-60),
             (-25,-50),(-20,-44),(-15,-42),(-10,-38),(-5,-36),(0,-50),(5,-60),(8,-70),(10,-78)],
            # Europe
            [(38,-10),(42,-8),(44,0),(48,0),(50,5),(52,5),(54,10),(56,12),(58,15),(60,25),
             (65,28),(70,30),(70,40),(65,42),(60,38),(58,30),(55,25),(52,20),(50,15),(48,12),
             (46,15),(44,12),(42,15),(40,20),(38,23),(36,22),(36,0),(38,-10)],
            # Africa
            [(35,-5),(37,10),(35,12),(33,10),(30,32),(25,35),(20,38),(15,42),(10,42),(5,40),(0,42),
             (-5,40),(-10,38),(-15,35),(-20,35),(-25,32),(-30,30),(-35,22),(-35,18),
             (-30,15),(-25,15),(-20,12),(-15,12),(-10,8),(-5,5),(0,2),(5,0),(5,-5),(10,-15),
             (15,-17),(20,-17),(25,-15),(28,-13),(32,-10),(35,-5)],
            # Asia (simplified)
            [(40,28),(42,45),(45,50),(50,55),(55,65),(60,70),(65,80),(68,100),(65,110),(60,120),
             (55,130),(50,140),(45,145),(40,140),(35,135),(30,122),(25,120),(20,110),(15,105),
             (10,100),(5,105),(8,98),(15,100),(25,90),(30,80),(28,65),(25,58),(30,50),(35,35),(40,28)],
            # Australia
            [(-15,130),(-12,135),(-15,140),(-18,148),(-25,152),(-30,150),(-35,148),(-38,145),
             (-35,140),(-32,135),(-28,130),(-25,115),(-22,115),(-18,122),(-15,130)],
        ]
        # City lights: (lat_deg, lon_deg) for major cities
        self._city_lights = [
            (40.7,-74), (34,-118), (41.9,-87.6), (51.5,0), (48.9,2.3), (52.5,13.4),
            (55.8,37.6), (35.7,51.4), (28.6,77.2), (31.2,121.5), (35.7,139.7),
            (39.9,116.4), (37.6,127), (-33.9,151.2), (-23.5,-46.6), (19.4,-99.1),
            (-34.6,-58.4), (30,31), (-1.3,36.8), (1.3,103.8), (13.7,100.5),
            (22.3,114.2), (-6.2,106.8), (33.9,-6.9), (6.5,3.4),
        ]
        self._cam_nodes = [
            (0.85, -0.45, "CAMERA 01"),
            (0.90, 0.20,  "CAMERA 02"),
            (-0.85, 0.55, "CAMERA 03"),
            (-0.80, -0.50, "CAMERA 04"),
        ]

        # Scene 5 – scan lines
        self._scan_lines = [rng.uniform(0.05, 0.95) for _ in range(28)]

        # Scene 6, 7 – detected objects mapping directly to visual street silhouettes
        self._det_objs = [
            (0.14, 0.50, 0.22, 0.81, "PERSON",  "#10B981", "95.2%", 12),
            (0.34, 0.47, 0.42, 0.78, "PERSON",  "#10B981", "92.4%", 13),
            (0.60, 0.60, 0.78, 0.82, "CAR",     "#3B82F6", "97.1%", 7),
            (0.39, 0.55, 0.415, 0.60, "PHONE",  "#A78BFA", "89.0%", 21),
        ]

        # Scene 8 – chart data
        self._chart_data = [rng.uniform(0.15, 0.85) for _ in range(22)]

        # Scene 2 – Brain synapses
        self._synapses = []
        for _ in range(18):
            if self._neuro_edges:
                edge_idx = rng.randint(0, len(self._neuro_edges) - 1)
                self._synapses.append({
                    "edge_idx": edge_idx,
                    "progress": rng.uniform(0.0, 1.0),
                    "speed": rng.uniform(0.8, 2.0)
                })

    # ── tick ─────────────────────────────────────────────────────────────────
    def _tick(self):
        if self._done:
            return
        self._t += TICK_MS / 1000.0

        # Update brain synapses progress
        if hasattr(self, '_synapses'):
            for s in self._synapses:
                s["progress"] += s["speed"] * (TICK_MS / 1000.0)
                if s["progress"] >= 1.0:
                    s["progress"] = 0.0
                    if self._neuro_edges:
                        s["edge_idx"] = random.randint(0, len(self._neuro_edges) - 1)

        if self._t >= TOTAL_SEC:
            self._skip_clicked()
        self.update()

    def _skip_clicked(self):
        if not self._done:
            self._done = True
            self._timer.stop()
            self.finished.emit()

    # ── mouse handler for SKIP button ────────────────────────────────────────
    # ── mouse handler for SKIP button ────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            mx, my = pos.x(), pos.y()
            w, h = self.width(), self.height()
            if w - 175 <= mx <= w - 10 and h - 40 <= my <= h - 8:
                self._skip_clicked()

    def mouseMoveEvent(self, event):
        pos = event.position()
        mx, my = pos.x(), pos.y()
        w, h = self.width(), self.height()
        hovered = (w - 175 <= mx <= w - 10) and (h - 40 <= my <= h - 8)
        if hovered != self._skip_hovered:
            self._skip_hovered = hovered
            self.update()

    # ── paintEvent: Fullscreen Sequential Slideshow ──────────────────────────
    def paintEvent(self, _ev):
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Ambient backdrop
        bg_glow = QRadialGradient(w // 2, h // 2, max(w, h) * 0.6)
        bg_glow.setColorAt(0, QColor(4, 15, 36, 255))
        bg_glow.setColorAt(0.6, QColor(2, 6, 16, 255))
        bg_glow.setColorAt(1.0, QColor(1, 2, 8, 255))
        p.fillRect(0, 0, w, h, QBrush(bg_glow))

        SCENE_DURATION = 4.0
        scene_idx = int(self._t // SCENE_DURATION)
        scene_idx = clamp(scene_idx, 0, 6)
        local_t = self._t - scene_idx * SCENE_DURATION

        # Calculate local sp (progress from 0.0 to 1.0 within the scene)
        sp = local_t / SCENE_DURATION

        # Calculate fade-in / fade-out opacity
        fade = 1.0
        if local_t < 0.5:
            fade = local_t / 0.5
        elif local_t > SCENE_DURATION - 0.5:
            fade = (SCENE_DURATION - local_t) / 0.5
        fade = clamp(fade, 0, 1)

        # Draw the active fullscreen scene
        p.save()
        p.setClipRect(QRectF(0, 0, w, h))

        if   scene_idx == 0: self._draw_scene1(p, w, h, sp, fade)
        elif scene_idx == 1: self._draw_scene3(p, w, h, sp, fade)
        elif scene_idx == 2: self._draw_scene5(p, w, h, sp, fade)
        elif scene_idx == 3: self._draw_scene6(p, w, h, sp, fade)
        elif scene_idx == 4: self._draw_scene7(p, w, h, sp, fade)
        elif scene_idx == 5: self._draw_scene8(p, w, h, sp, fade)
        elif scene_idx == 6: self._draw_scene9(p, w, h, sp, fade)

        p.restore()

        # Overall Outer Border Brackets (HUD overlay)
        self._draw_brackets(p, w, h, fade, scene_idx)

        # Bottom Skip Button
        self._draw_skip_button(p, w, h, fade)
        p.end()

    # ── neon glow graphics helpers ───────────────────────────────────────────
    def _draw_neon_line(self, p, p1, p2, color, width=1):
        pen1 = QPen(QColor(color.red(), color.green(), color.blue(), 25), width * 4)
        p.setPen(pen1)
        p.drawLine(p1, p2)
        pen2 = QPen(QColor(color.red(), color.green(), color.blue(), 95), width * 2)
        p.setPen(pen2)
        p.drawLine(p1, p2)
        pen3 = QPen(QColor(255, 255, 255, 220), max(1, width // 2))
        p.setPen(pen3)
        p.drawLine(p1, p2)

    def _draw_neon_ellipse(self, p, center, rx, ry, color, width=1):
        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 25), width * 4))
        p.drawEllipse(center, rx, ry)
        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 95), width * 2))
        p.drawEllipse(center, rx, ry)
        p.setPen(QPen(QColor(255, 255, 255, 220), max(1, width // 2)))
        p.drawEllipse(center, rx, ry)

    def _draw_hologram_projection_cone(self, p, w, h, cx, cy_base, rx, fade):
        cone_path = QPainterPath()
        cone_path.moveTo(cx - rx, cy_base)
        cone_path.lineTo(cx - rx * 0.4, cy_base - h * 0.5)
        cone_path.lineTo(cx + rx * 0.4, cy_base - h * 0.5)
        cone_path.lineTo(cx + rx, cy_base)
        cone_path.closeSubpath()

        cone_grad = QLinearGradient(cx, cy_base, cx, cy_base - h * 0.5)
        cone_grad.setColorAt(0, QColor(0, 229, 255, int(42 * fade)))
        cone_grad.setColorAt(0.5, QColor(0, 229, 255, int(15 * fade)))
        cone_grad.setColorAt(1.0, QColor(0, 229, 255, 0))

        p.setBrush(QBrush(cone_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(cone_path)

    # ── street view vector background (Scenes 5, 6, 7) ──────────────────────
    def _draw_street_scene(self, p, w, h, fade):
        if hasattr(self, 'street_pixmap') and not self.street_pixmap.isNull():
            # Draw the loaded high-quality street scene image scaled to cell dimensions
            p.setOpacity(fade * 0.65)
            p.drawPixmap(QRect(0, 0, w, h), self.street_pixmap)
            p.setOpacity(1.0)
            
            # Subtle cyan-obsidian tint layer to make HUD overlay pop
            p.fillRect(QRect(0, 0, w, h), QColor(4, 10, 24, int(100 * fade)))
        else:
            # Fallback to vector-drawn street scene
            # Sky
            p.fillRect(QRectF(0, 0, w, h * 0.4), QColor(5, 7, 14, int(255 * fade)))
            
            # Wet Asphalt perspective road
            road_path = QPainterPath()
            road_path.moveTo(w * 0.35, h * 0.4)
            road_path.lineTo(w * 0.65, h * 0.4)
            road_path.lineTo(w * 0.95, h * 1.0)
            road_path.lineTo(w * 0.05, h * 1.0)
            road_path.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(11, 16, 26, int(255 * fade)))
            p.drawPath(road_path)
            
            # Sidewalks
            p.setBrush(QColor(18, 24, 38, int(255 * fade)))
            sw_left = QPainterPath()
            sw_left.moveTo(0, h * 0.4)
            sw_left.lineTo(w * 0.35, h * 0.4)
            sw_left.lineTo(w * 0.05, h * 1.0)
            sw_left.lineTo(0, h * 1.0)
            sw_left.closeSubpath()
            p.drawPath(sw_left)
            
            sw_right = QPainterPath()
            sw_right.moveTo(w * 0.65, h * 0.4)
            sw_right.lineTo(w, h * 0.4)
            sw_right.lineTo(w, h * 1.0)
            sw_right.lineTo(w * 0.95, h * 1.0)
            sw_right.closeSubpath()
            p.drawPath(sw_right)
            
            # Cyberpunk perspective buildings
            p.setBrush(QColor(6, 9, 16, int(255 * fade)))
            p.drawRect(QRectF(0, h * 0.1, w * 0.26, h * 0.3))
            p.drawRect(QRectF(w * 0.74, h * 0.1, w * 0.26, h * 0.3))
            
            # Neon street lamp post
            p.setPen(QPen(QColor(0, 229, 255, int(180 * fade)), 1.5))
            p.drawLine(QPointF(w * 0.12, h * 0.4), QPointF(w * 0.12, h * 0.15))
            p.drawLine(QPointF(w * 0.12, h * 0.15), QPointF(w * 0.16, h * 0.15))
            lamp_glow = QRadialGradient(w * 0.16, h * 0.15, int(w * 0.06))
            lamp_glow.setColorAt(0, QColor(0, 229, 255, int(100 * fade)))
            lamp_glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(lamp_glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(w * 0.16, h * 0.15), int(w * 0.06), int(w * 0.06))
            
            # Wet Asphalt reflection glows
            p.setPen(QPen(QColor(0, 229, 255, int(35 * fade)), 1.5))
            p.drawLine(QPointF(w * 0.2, h * 0.6), QPointF(w * 0.35, h * 0.6))
            p.drawLine(QPointF(w * 0.45, h * 0.82), QPointF(w * 0.72, h * 0.82))
            p.drawLine(QPointF(w * 0.15, h * 0.94), QPointF(w * 0.52, h * 0.94))
            p.setPen(QPen(QColor(59, 130, 246, int(30 * fade)), 1.5))
            p.drawLine(QPointF(w * 0.35, h * 0.7), QPointF(w * 0.55, h * 0.7))

            # Pedestrian 1 Silhouette
            px1 = w * 0.18
            py1 = h * 0.52
            p.setBrush(QColor(2, 4, 8, int(220 * fade)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px1, py1), int(h * 0.025), int(h * 0.025))
            p.drawRect(QRectF(px1 - w * 0.015, py1 + h * 0.025, w * 0.03, h * 0.14))
            p.setPen(QPen(QColor(2, 4, 8, int(220 * fade)), 2.5))
            p.drawLine(QPointF(px1 - w * 0.007, py1 + h * 0.165), QPointF(px1 - w * 0.012, py1 + h * 0.27))
            p.drawLine(QPointF(px1 + w * 0.007, py1 + h * 0.165), QPointF(px1 + w * 0.012, py1 + h * 0.27))

            # Pedestrian 2 Silhouette
            px2 = w * 0.38
            py2 = h * 0.49
            p.setBrush(QColor(2, 4, 8, int(220 * fade)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px2, py2), int(h * 0.022), int(h * 0.022))
            p.drawRect(QRectF(px2 - w * 0.012, py2 + h * 0.022, w * 0.024, h * 0.13))
            p.setPen(QPen(QColor(2, 4, 8, int(220 * fade)), 2))
            p.drawLine(QPointF(px2 - w * 0.005, py2 + h * 0.152), QPointF(px2 - w * 0.01, py2 + h * 0.25))
            p.drawLine(QPointF(px2 + w * 0.005, py2 + h * 0.152), QPointF(px2 + w * 0.01, py2 + h * 0.25))

            # Car Silhouette
            cx2 = w * 0.60
            cy2 = h * 0.60
            p.setBrush(QColor(0, 0, 0, int(255 * fade)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx2 + w * 0.03, cy2 + h * 0.16), int(h * 0.028), int(h * 0.028))
            p.drawEllipse(QPointF(cx2 + w * 0.12, cy2 + h * 0.16), int(h * 0.028), int(h * 0.028))
            p.setBrush(QColor(4, 7, 14, int(230 * fade)))
            p.drawRect(QRectF(cx2, cy2 + h * 0.06, w * 0.15, h * 0.1))
            p.drawRect(QRectF(cx2 + w * 0.02, cy2, w * 0.11, h * 0.06))

    # =========================================================================
    # SCENE 1 – SYSTEM BOOT
    # =========================================================================
    def _draw_scene1(self, p, w, h, sp, fade):
        t = self._t
        self._draw_grid(p, w, h, alpha=int(14 * fade))

        cx, cy = w // 2, h // 2
        cy_base = cy + int(h * 0.28)
        rx = int(w * 0.22)

        self._draw_hologram_projection_cone(p, w, h, cx, cy_base, rx, fade)
        p.setBrush(Qt.BrushStyle.NoBrush)
        self._draw_neon_ellipse(p, QPointF(cx, cy_base), rx, int(rx * 0.28), QColor(0, 229, 255), 2)

        glw = QRadialGradient(cx, cy_base, rx)
        glw.setColorAt(0.6, QColor(0, 229, 255, 0))
        glw.setColorAt(0.85, QColor(0, 229, 255, int(35 * fade)))
        glw.setColorAt(1.0,  QColor(0, 229, 255, 0))
        p.setBrush(QBrush(glw))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy_base), rx, int(rx * 0.28))

        # Accent rings
        for ri in range(3):
            angle = t * 1.2 + ri * math.tau / 3
            rx2 = int(w * 0.28)
            ry2 = int(h * 0.28)
            dx = int(cx + rx2 * math.cos(angle))
            dy = int(cy_base + ry2 * math.sin(angle) * 0.25)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 229, 255, int(220 * fade)))
            p.drawEllipse(QPointF(dx, dy), 3, 3)

        # Title
        alpha_logo = int(255 * ease_in_out(clamp(sp * 2.5, 0, 1)))
        self._draw_title(p, w, h, alpha_logo, subtitle="HOLOGRAPHIC CORE")

        # Loading Bars
        bar_alpha = int(255 * ease_in_out(clamp((sp - 0.1) * 2.5, 0, 1)))
        if bar_alpha > 0:
            bar_y0 = cy + int(h * 0.05)
            bar_w  = int(w * 0.38)
            bar_h  = max(6, int(h * 0.04))
            gap    = int(h * 0.09)
            bar_x  = cx - bar_w // 2
            
            for i, bar_info in enumerate(self._bars):
                prog = clamp((sp - 0.15 - i * 0.1) * 3, 0, 1)
                by   = bar_y0 + i * gap
                
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(10, 20, 40, int(160 * fade)))
                p.drawRoundedRect(bar_x, by, bar_w, bar_h, 2, 2)
                
                seg_w = max(2, int(w * 0.015))
                seg_gap = 2
                n_segs = int(bar_w / (seg_w + seg_gap))
                active_segs = int(n_segs * prog)
                
                for s in range(active_segs):
                    sx = bar_x + s * (seg_w + seg_gap)
                    if s == active_segs - 1 and prog < 1.0:
                        p.setBrush(QColor(255, 255, 255, bar_alpha))
                    else:
                        p.setBrush(QColor(0, 229, 255, int(200 * fade)))
                    p.drawRect(sx, by, seg_w, bar_h)

                p.setPen(QPen(QColor(0, 229, 255, bar_alpha // 3), 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(bar_x, by, bar_w, bar_h, 2, 2)
                
                f = QFont("Courier New", max(5, int(h * 0.03)), QFont.Weight.Bold)
                p.setFont(f)
                p.setPen(QColor(148, 163, 184, bar_alpha))
                p.drawText(bar_x, by - 3, bar_info["label"].upper())

        # Status text
        status_a = int(200 * fade)
        f = QFont("Courier New", max(6, int(h * 0.035)))
        p.setFont(f)
        p.setPen(QColor(100, 180, 255, status_a))
        p.drawText(QRectF(0, h - 36, w, 20), Qt.AlignmentFlag.AlignCenter, "SYSTEM INITIALIZING...")

    # =========================================================================
    # SCENE 2 – AI CORE ACTIVATION
    # =========================================================================
    def _draw_scene2(self, p, w, h, sp, fade):
        t = self._t
        self._draw_grid(p, w, h, alpha=10)
        cx, cy = w // 2, h // 2

        # ── Holographic Shield Scan ──────────────────────────────
        shield_r = int(min(w, h) * 0.25)
        for i, rad_offset in enumerate([0, -30, -60, -90]):
            r_val = shield_r + rad_offset
            if r_val <= 0:
                continue
            pulse_factor = 1.0 + 0.02 * math.sin(t * 4.0 + i)
            curr_r = int(r_val * pulse_factor)
            
            pen_color = QColor(0, 229, 255, int((100 - i * 20) * fade))
            p.setPen(QPen(pen_color, 1.2, Qt.PenStyle.DashLine if i % 2 == 0 else Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), curr_r, int(curr_r * 0.85))

        sweep_angle = (t * 2.0) % 360.0
        ex = cx + shield_r * math.cos(math.radians(sweep_angle))
        ey = cy + shield_r * 0.85 * math.sin(math.radians(sweep_angle))
        
        beam_grad = QLinearGradient(cx, cy, ex, ey)
        beam_grad.setColorAt(0, QColor(0, 229, 255, 0))
        beam_grad.setColorAt(0.7, QColor(0, 229, 255, int(150 * fade)))
        beam_grad.setColorAt(1.0, QColor(0, 229, 255, 0))
        p.setPen(QPen(QBrush(beam_grad), 2.0))
        p.drawLine(QPointF(cx, cy), QPointF(ex, ey))

        p.setPen(QPen(QColor(0, 229, 255, int(45 * fade)), 1))
        for angle_deg in range(0, 360, 45):
            rad = math.radians(angle_deg)
            p.drawLine(QPointF(cx + 40 * math.cos(rad), cy + 40 * 0.85 * math.sin(rad)),
                       QPointF(cx + shield_r * math.cos(rad), cy + shield_r * 0.85 * math.sin(rad)))

        core_pulse = 1.0 + 0.08 * math.sin(t * 6.0)
        core_r = int(24 * core_pulse)
        core_grad = QRadialGradient(cx, cy, core_r)
        core_grad.setColorAt(0, QColor(0, 229, 255, int(220 * fade)))
        core_grad.setColorAt(0.5, QColor(0, 229, 255, int(90 * fade)))
        core_grad.setColorAt(1.0, QColor(0, 229, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(core_grad))
        p.drawEllipse(QPointF(cx, cy), core_r, int(core_r * 0.85))

        box_r = int(36 * (1.0 + 0.05 * math.cos(t * 3.0)))
        p.setPen(QPen(QColor(0, 229, 255, int(120 * fade)), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(cx - box_r, cy - int(box_r * 0.85), box_r * 2, int(box_r * 2 * 0.85))

        nodes_count = 15
        for i in range(nodes_count):
            angle = (t * 0.15 + i * (2.0 * math.pi / nodes_count)) % (2.0 * math.pi)
            dist = shield_r * (0.35 + 0.5 * math.sin(t * 0.5 + i))
            nx = cx + dist * math.cos(angle)
            ny = cy + dist * 0.85 * math.sin(angle)
            
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 229, 255, int(180 * fade * (0.4 + 0.6 * math.sin(t * 4.0 + i)))))
            p.drawEllipse(QPointF(nx, ny), 3, 3)
            
            if i % 3 == 0:
                p.setPen(QPen(QColor(0, 229, 255, int(35 * fade)), 0.6))
                p.drawLine(QPointF(cx, cy), QPointF(nx, ny))

        diags = [
            ("CPU", "92%",  "#00E5FF", -0.32, -0.26),
            ("GPU", "94%",  "#3B82F6",  0.32, -0.26),
            ("MEM", "78%",  "#A78BFA", -0.32,  0.26),
            ("NET", "89%",  "#10B981",  0.32,  0.26),
        ]
        card_a = int(255 * ease_in_out(clamp((sp - 0.25) * 3, 0, 1)))
        if card_a > 0:
            for label, val, col_hex, dx, dy in diags:
                bx = cx + int(dx * w) - 28
                by = cy + int(dy * h) - 15
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(8, 16, 30, int(180 * card_a / 255)))
                p.drawRoundedRect(bx, by, 56, 30, 3, 3)
                col = QColor(col_hex); col.setAlpha(card_a)
                p.setPen(QPen(col, 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(bx, by, 56, 30, 3, 3)
                
                val_int = int(val.replace("%", ""))
                if sp >= 1.0:
                    val_int = clamp(val_int + int(2 * math.sin(t * 3.5 + bx)), 10, 99)
                val_str = f"{val_int}%"
                
                f = QFont("Courier New", max(5, int(h * 0.025)), QFont.Weight.Bold)
                p.setFont(f)
                p.setPen(QColor(148, 163, 184, card_a))
                p.drawText(bx + 4, by + 10, label)
                f2 = QFont("Courier New", max(6, int(h * 0.038)), QFont.Weight.Bold)
                p.setFont(f2)
                p.setPen(col)
                p.drawText(bx + 4, by + 24, val_str)

        ta = int(255 * ease_in_out(clamp((sp - 0.3) * 3, 0, 1)))
        self._draw_status_line(p, w, h, "AI CORE ONLINE", QColor(0, 229, 255, ta))

    # =========================================================================
    # SCENE 3 – HOLOGRAPHIC LOGO REVEAL
    # =========================================================================
    def _draw_scene3(self, p, w, h, sp, fade):
        t = self._t
        cx, cy = w // 2, h // 2
        cy_base = cy + int(h * 0.28)
        rx = int(w * 0.22)

        self._draw_hologram_projection_cone(p, w, h, cx, cy_base, rx, fade)
        self._draw_neon_ellipse(p, QPointF(cx, cy_base), rx, int(rx * 0.28), QColor(0, 229, 255), 1)
        self._draw_starfield(p, w, h, t, int(50 * fade))

        # Particles
        prog = ease_in_out(clamp(sp * 1.6, 0, 1))
        for sx, sy, tx, ty, sz, base_a in self._conv_pts:
            px = lerp(sx * w, tx * w, prog)
            py = lerp(sy * h, ty * h, prog)
            trail_a = int(base_a * fade * (1.0 - prog * 0.6))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 229, 255, trail_a))
            p.drawEllipse(QPointF(px, py), sz * 0.7, sz * 0.7)

        # Expanding rings
        if sp > 0.6:
            ring_t = ease_in_out(clamp((sp - 0.6) / 0.4, 0, 1))
            for ri in range(3):
                rr = int((30 + ri * 25) * ring_t)
                ra = int(180 * (1.0 - ring_t) * fade)
                p.setPen(QPen(QColor(0, 229, 255, ra), 1.5 - ri * 0.3))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(cx, cy), rr, int(rr * 0.6))

        # Bloom lens flare
        if sp > 0.62:
            lf_a = int(220 * (1.0 - ease_in_out(clamp((sp - 0.62) * 2.5, 0, 1))) * fade)
            gf = QRadialGradient(cx, cy, int(w * 0.18))
            gf.setColorAt(0, QColor(255, 255, 255, lf_a))
            gf.setColorAt(0.3, QColor(0, 229, 255, lf_a // 2))
            gf.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(gf))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), int(w * 0.18), int(w * 0.18))

            # Cinematic horizontal anamorphic flare line
            p.setPen(QPen(QColor(0, 229, 255, int(lf_a * 0.85)), 2))
            p.drawLine(QPointF(0, cy), QPointF(w, cy))

        # Logo Reveal
        logo_a = int(255 * ease_in_out(clamp((sp - 0.5) * 3, 0, 1)))
        if logo_a > 0:
            self._draw_big_logo(p, w, h, logo_a, t)

    # =========================================================================
    # SCENE 4 – GLOBAL RADAR SCAN
    # =========================================================================
    def _draw_scene4(self, p, w, h, sp, fade):
        t = self._t
        cx, cy = w // 2, h // 2
        self._draw_starfield(p, w, h, t, 35)

        # Draw background matrix grid lines
        grid_cols = 7
        grid_rows = 5
        cell_w = w * 0.12
        cell_h = h * 0.12
        start_x = cx - (grid_cols - 1) * cell_w / 2
        start_y = cy - (grid_rows - 1) * cell_h / 2

        # Drawing the lattice connection lines
        p.setPen(QPen(QColor(0, 229, 255, int(25 * fade)), 0.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for r in range(grid_rows):
            for c in range(grid_cols):
                x = start_x + c * cell_w
                y = start_y + r * cell_h
                if c < grid_cols - 1:
                    p.drawLine(QPointF(x, y), QPointF(x + cell_w, y))
                if r < grid_rows - 1:
                    p.drawLine(QPointF(x, y), QPointF(x, y + cell_h))
                if c < grid_cols - 1 and r < grid_rows - 1 and (c + r) % 2 == 0:
                    p.drawLine(QPointF(x, y), QPointF(x + cell_w, y + cell_h))

        # Dynamic data packets traveling along connection lines
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 255, 80, int(180 * fade)))
        for r in range(grid_rows):
            for c in range(grid_cols):
                x = start_x + c * cell_w
                y = start_y + r * cell_h
                if c < grid_cols - 1:
                    packet_prog = (t * 0.8 + (c * 0.15) + (r * 0.23)) % 1.0
                    px = x + packet_prog * cell_w
                    p.drawEllipse(QPointF(px, y), 2.2, 2.2)
                if r < grid_rows - 1:
                    packet_prog = (t * 0.7 + (c * 0.31) + (r * 0.08)) % 1.0
                    py = y + packet_prog * cell_h
                    p.drawEllipse(QPointF(x, py), 2.2, 2.2)

        # Drawing the grid nodes
        for r in range(grid_rows):
            for c in range(grid_cols):
                x = start_x + c * cell_w
                y = start_y + r * cell_h
                pulse_val = 0.5 + 0.5 * math.sin(t * 3.0 + r * 1.5 + c * 2.1)
                node_a = int((100 + pulse_val * 155) * fade)
                if (c + r) % 3 == 0:
                    p.setPen(QPen(QColor(0, 229, 255, node_a), 1))
                    p.setBrush(QColor(0, 229, 255, int(40 * fade)))
                    p.drawEllipse(QPointF(x, y), 4.5, 4.5)
                    p.setPen(QPen(QColor(0, 229, 255, int(node_a * 0.5)), 0.6))
                    p.drawEllipse(QPointF(x, y), 8.0 * (1.0 + 0.15 * pulse_val), 8.0 * (1.0 + 0.15 * pulse_val))
                else:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(0, 229, 255, int(node_a * 0.8)))
                    p.drawEllipse(QPointF(x, y), 2.5, 2.5)

        # Radar Sweep Scan overlay
        sweep_r = int(min(w, h) * 0.35)
        sweep_angle = (t * 1.2) % math.tau
        wpath = QPainterPath()
        wpath.moveTo(cx, cy)
        for deg in range(40):
            a = sweep_angle - math.radians(deg)
            wpath.lineTo(cx + sweep_r * math.cos(a),
                         cy + sweep_r * 0.85 * math.sin(a))
        wpath.closeSubpath()
        p.setBrush(QColor(0, 255, 80, int(25 * fade)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(wpath)
        p.setPen(QPen(QColor(0, 255, 80, int(150 * fade)), 1.5))
        p.drawLine(QPointF(cx, cy), QPointF(cx + sweep_r * math.cos(sweep_angle), cy + sweep_r * 0.85 * math.sin(sweep_angle)))

        # Outer frame details
        p.setPen(QPen(QColor(0, 229, 255, int(80 * fade)), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), sweep_r, int(sweep_r * 0.85))

        # Camera Node labels mapped to grid positions
        f_cam = QFont("Courier New", max(5, int(h * 0.018)), QFont.Weight.Bold)
        p.setFont(f_cam)
        cam_grid_positions = [
            (1, 1), # Camera 01
            (1, 5), # Camera 02
            (3, 1), # Camera 03
            (3, 5), # Camera 04
        ]
        for i, (cam_row, cam_col) in enumerate(cam_grid_positions):
            if i >= len(self._cam_nodes):
                break
            cam_label = self._cam_nodes[i][2]
            node_x = start_x + cam_col * cell_w
            node_y = start_y + cam_row * cell_h
            offset_dir = -1.0 if cam_col < grid_cols / 2 else 1.0
            gx = node_x + offset_dir * (cell_w * 0.9)
            gy = node_y + (cell_h * 0.4 if cam_row < grid_rows / 2 else -cell_h * 0.4)
            p.setPen(QPen(QColor(0, 229, 255, int(80 * fade)), 1.2, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(node_x, node_y), QPointF(gx, gy))
            bw, bh = 85, 28
            bx = gx - bw // 2
            by = gy - bh // 2
            p.setPen(QPen(QColor(0, 229, 255, int(120 * fade)), 1))
            p.setBrush(QColor(4, 15, 35, int(200 * fade)))
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 3, 3)

            p.setPen(QColor(0, 229, 255, int(230 * fade)))
            p.drawText(QRectF(bx, by, bw, bh * 0.55), Qt.AlignmentFlag.AlignCenter, cam_label)
            p.setPen(QColor(0, 255, 80, int(200 * fade)))
            p.drawText(QRectF(bx, by + bh * 0.4, bw, bh * 0.55), Qt.AlignmentFlag.AlignCenter, "ONLINE")

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 255, 80, int(230 * fade * (0.5 + 0.5 * math.sin(t * 3 + i)))))
            p.drawEllipse(QPointF(bx + 8, gy), 3, 3)

        self._draw_status_line(p, w, h, "GLOBAL NETWORK ACTIVE", QColor(0, 255, 80, int(200 * fade)))

    # =========================================================================
    # SCENE 5 – CAMERA FEED INITIATION
    # =========================================================================
    def _draw_scene5(self, p, w, h, sp, fade):
        t = self._t
        cx, cy = w // 2, h // 2

        # Perspective street scene backing
        self._draw_street_scene(p, w, h, fade)

        # Scanning grid lines overlay
        p.setPen(QPen(QColor(0, 229, 255, int(12 * fade)), 1))
        for yf in self._scan_lines:
            py = int(yf * h)
            p.drawLine(0, py, w, py)

        # Scrolling diagnostics logs in fullscreen overlay
        f_log = QFont("Courier New", max(5, int(h * 0.024)), QFont.Weight.Bold)
        p.setFont(f_log)
        p.setPen(QColor(0, 229, 255, int(180 * fade)))
        logs = [
            "SYS_LINK: ESTABLISHED",
            "DECODING H.264 CAMERA BITSTREAM...",
            "FPS: 60.00 | BANDWIDTH: 45MB/s",
            "AGC: ENABLED | DZOOM: 1.0x",
            "LENS FOCUS: LOCKING RETICLE...",
        ]
        for li, log_t in enumerate(logs):
            p.drawText(40, 60 + li * 20, log_t)

        # Focus Aperture
        aperture_r = int(h * 0.28 * (1.0 - ease_in_out(clamp(sp * 1.8, 0, 1)) * 0.58))
        n_blades = 8
        p.setPen(QPen(QColor(0, 229, 255, int(130 * fade)), 1.2))
        for i in range(n_blades):
            angle = t * 0.75 + i * math.tau / n_blades
            x1 = cx + aperture_r * math.cos(angle)
            y1 = cy + aperture_r * math.sin(angle)
            tang_x = -math.sin(angle) * aperture_r * 0.85
            tang_y =  math.cos(angle) * aperture_r * 0.85
            p.drawLine(QPointF(x1, y1), QPointF(x1 + tang_x, y1 + tang_y))

        # Focus Reticle
        ret_a = int(220 * ease_in_out(clamp((sp - 0.2) * 3, 0, 1)) * fade)
        if ret_a > 0:
            ret_r = int(h * 0.09)
            self._draw_neon_ellipse(p, QPointF(cx, cy), ret_r, ret_r, QColor(0, 229, 255), 1.5)
            
            p.setPen(QPen(QColor(0, 229, 255, ret_a), 1.5))
            p.drawLine(cx - ret_r - 12, cy, cx - ret_r + 4, cy)
            p.drawLine(cx + ret_r - 4, cy, cx + ret_r + 12, cy)
            p.drawLine(cx, cy - ret_r - 12, cx, cy - ret_r + 4)
            p.drawLine(cx, cy + ret_r - 4, cx, cy + ret_r + 12)
            
            pulse_r = int(ret_r + 12 + 5 * math.sin(t * 5.5))
            p.setPen(QPen(QColor(0, 229, 255, int(ret_a * 0.45)), 1))
            p.drawEllipse(QPointF(cx, cy), pulse_r, pulse_r)

            lock_p = ease_in_out(clamp((sp - 0.5) * 3, 0, 1))
            lock_a = int(lock_p * ret_a)
            f = QFont("Courier New", max(6, int(h * 0.035)), QFont.Weight.Bold)
            p.setFont(f)
            p.setPen(QColor(0, 229, 255, lock_a))
            p.drawText(QRectF(cx - 60, cy + ret_r + 6, 120, 16), Qt.AlignmentFlag.AlignCenter, "LOCK ON")

        # Corner HUD brackets
        bl = 18
        p.setPen(QPen(QColor(0, 229, 255, int(150 * fade)), 1.5))
        for ox, oy, sx2, sy2 in [
            (40, 40, 1, 1), (w-40, 40, -1, 1),
            (40, h-40, 1, -1), (w-40, h-40, -1, -1)
        ]:
            p.drawLine(ox, oy, ox + sx2 * bl, oy)
            p.drawLine(ox, oy, ox, oy + sy2 * bl)

        self._draw_status_line(p, w, h, "CAMERA FEED INITIALIZED", QColor(0, 255, 128, int(200 * fade)))

    # =========================================================================
    # SCENE 6 – OBJECT DETECTION
    # =========================================================================
    def _draw_scene6(self, p, w, h, sp, fade):
        t = self._t
        # Street scene backdrop
        self._draw_street_scene(p, w, h, fade)

        # Scanning laser sweep bar
        laser_y = int(((t * 0.4) % 1.0) * h)
        p.setPen(QPen(QColor(0, 229, 255, int(15 * fade)), 5))
        p.drawLine(0, laser_y, w, laser_y)
        p.setPen(QPen(QColor(255, 255, 255, int(210 * fade)), 1.5))
        p.drawLine(0, laser_y, w, laser_y)

        # Detected objects side HUD overlay list
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(6, 12, 24, int(160 * fade)))
        p.drawRoundedRect(QRectF(w - 180, 50, 160, 120), 4, 4)
        p.setPen(QPen(QColor(0, 229, 255, int(70 * fade)), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(w - 180, 50, 160, 120), 4, 4)
        
        f_hud = QFont("Courier New", max(5, int(h * 0.024)), QFont.Weight.Bold)
        p.setFont(f_hud)
        p.setPen(QColor(0, 229, 255, int(220 * fade)))
        p.drawText(w - 170, 70, "DETECTED TARGETS")
        
        for idx_o, (x1f, y1f, x2f, y2f, label, col_hex, conf, oid) in enumerate(self._det_objs):
            delay = idx_o * 0.15
            box_t = ease_in_out(clamp((sp - delay) * 3.5, 0, 1))
            if box_t > 0:
                p.setPen(QColor(col_hex))
                p.drawText(w - 170, 90 + idx_o * 18, f"> {label} ({conf})")
        p.restore()

        # Draw glowing detection boxes matching the pedestrians/cars precisely
        for i, (x1f, y1f, x2f, y2f, label, col_hex, conf, oid) in enumerate(self._det_objs):
            delay = i * 0.15
            box_t = ease_in_out(clamp((sp - delay) * 3.5, 0, 1))
            if box_t <= 0:
                continue

            bx1 = int(x1f * w); by1 = int(y1f * h)
            bx2 = int(x2f * w); by2 = int(y2f * h)
            bw  = bx2 - bx1;    bh  = by2 - by1
            col = QColor(col_hex)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(col.red(), col.green(), col.blue(), int(15 * box_t * fade)))
            p.drawRect(bx1, by1, bw, bh)

            p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), int(65 * box_t * fade)), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(bx1, by1, bw, bh)

            # Bounding Box Corners
            blen = int(min(bw, bh) * 0.2 * box_t)
            p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), int(230 * box_t * fade)), 2))
            p.drawLine(bx1, by1, bx1 + blen, by1)
            p.drawLine(bx1, by1, bx1, by1 + blen)
            p.drawLine(bx2, by1, bx2 - blen, by1)
            p.drawLine(bx2, by1, bx2, by1 + blen)
            p.drawLine(bx1, by2, bx1 + blen, by2)
            p.drawLine(bx1, by2, bx1, by2 - blen)
            p.drawLine(bx2, by2, bx2 - blen, by2)
            p.drawLine(bx2, by2, bx2, by2 - blen)

            # Label banner
            la = int(225 * box_t * fade)
            p.setBrush(QColor(col.red(), col.green(), col.blue(), int(195 * box_t * fade)))
            p.setPen(Qt.PenStyle.NoPen)
            badge_h = 13
            p.drawRect(bx1, by1 - badge_h, max(20, int(bw * box_t)), badge_h)
            
            f = QFont("Courier New", max(5, int(h * 0.035)), QFont.Weight.Bold)
            p.setFont(f)
            p.setPen(QColor(0, 0, 0, la))
            p.drawText(bx1 + 3, by1 - 3, f"{label} {conf}")

        self._draw_status_line(p, w, h, "OBJECT DETECTION ACTIVE", QColor(0, 229, 255, int(200 * fade)))

    # =========================================================================
    # SCENE 7 – TRACKING SYSTEM ACTIVE
    # =========================================================================
    def _draw_scene7(self, p, w, h, sp, fade):
        t = self._t
        # Street scene backing
        self._draw_street_scene(p, w, h, fade)

        # Draw Fading Neon Trail Vectors projecting into perspective
        for i, (x1f, y1f, x2f, y2f, label, col_hex, conf, oid) in enumerate(self._det_objs):
            col = QColor(col_hex)
            cx_base = (x1f + x2f) / 2 * w
            cy_base = y2f * h

            # Generate perspective trails curving backwards
            trail_pts = []
            n_pts = int(30 * sp)
            for k in range(n_pts):
                t_val = k / 30.0
                px = cx_base - math.sin(t_val * 4.5 + i) * w * 0.06 * t_val
                py = cy_base + t_val * h * 0.22
                trail_pts.append(QPointF(px, py))

            # Render trail
            for j in range(1, len(trail_pts)):
                alpha = int(190 * (j / len(trail_pts)) * fade)
                p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), int(alpha * 0.25)), 4))
                p.drawLine(trail_pts[j-1], trail_pts[j])
                p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), alpha), 1.2))
                p.drawLine(trail_pts[j-1], trail_pts[j])

            # Flowing dots along trails to visualize movement vector direction
            if len(trail_pts) > 1:
                flow_idx = int((t * 20.0) % len(trail_pts))
                if flow_idx < len(trail_pts):
                    flow_pt = trail_pts[flow_idx]
                    p.setBrush(QColor(255, 255, 255, int(200 * fade)))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(flow_pt, 2, 2)

            # Draw current position dot & lock badge
            if trail_pts:
                tx = trail_pts[0].x()
                ty = trail_pts[0].y()
                p.setBrush(QColor(col.red(), col.green(), col.blue(), int(230 * fade)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(tx, ty), 3, 3)
                
                # Glowing ID badge
                badge_w = 30; badge_h = 13
                bx = int(tx) - badge_w // 2
                by = int(ty) - 18
                p.setBrush(QColor(col.red(), col.green(), col.blue(), int(185 * fade)))
                p.drawRoundedRect(bx, by, badge_w, badge_h, 2, 2)
                p.setPen(QColor(0, 0, 0, int(220 * fade)))
                f = QFont("Courier New", max(5, int(h * 0.025)), QFont.Weight.Bold)
                p.setFont(f)
                p.drawText(QRectF(bx, by, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, f"ID:{oid}")

        # Top status cards
        hud_a = int(220 * ease_in_out(clamp((sp - 0.1) * 3, 0, 1)) * fade)
        if hud_a > 0:
            counters = [
                ("FPS", "60.0", "#00E5FF"),
                ("TRACKS", str(len(self._det_objs)), "#10B981"),
                ("DETECTIONS", str(len(self._det_objs)), "#3B82F6"),
            ]
            card_w = int(w * 0.25)
            gap = int(w * 0.04)
            total_w = len(counters) * card_w + (len(counters) - 1) * gap
            sx = (w - total_w) // 2
            sy = 30
            for j, (lbl, val, ch) in enumerate(counters):
                bx = sx + j * (card_w + gap)
                col_c = QColor(ch); col_c.setAlpha(hud_a)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(6, 12, 24, int(190 * fade)))
                p.drawRoundedRect(bx, sy, card_w, 36, 3, 3)
                p.setPen(QPen(col_c, 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(bx, sy, card_w, 36, 3, 3)
                
                f = QFont("Courier New", max(5, int(h * 0.025)))
                p.setFont(f)
                p.setPen(QColor(148, 163, 184, hud_a))
                p.drawText(QRectF(bx, sy + 3, card_w, 11), Qt.AlignmentFlag.AlignCenter, lbl)
                
                f2 = QFont("Courier New", max(6, int(h * 0.038)), QFont.Weight.Bold)
                p.setFont(f2)
                p.setPen(col_c)
                p.drawText(QRectF(bx, sy + 15, card_w, 18), Qt.AlignmentFlag.AlignCenter, val)

        self._draw_status_line(p, w, h, "MULTIPLE OBJECT TRACKING ACTIVE", QColor(16, 185, 129, int(200 * fade)))

    # =========================================================================
    # SCENE 8 – ANALYTICS DASHBOARD
    # =========================================================================
    def _draw_scene8(self, p, w, h, sp, fade):
        slide = ease_in_out(clamp(sp * 1.8, 0, 1))

        # Panel frame
        panel_w = int(w * 0.88); panel_h = int(h * 0.72)
        px = int(w * 0.06 + (1.0 - slide) * w)
        py = int(h * 0.14)
        
        panel_grad = QLinearGradient(px, py, px + panel_w, py + panel_h)
        panel_grad.setColorAt(0, QColor(8, 16, 32, int(210 * fade)))
        panel_grad.setColorAt(1, QColor(4, 8, 20, int(210 * fade)))
        p.setBrush(QBrush(panel_grad))
        p.setPen(QPen(QColor(0, 229, 255, int(120 * fade)), 1))
        p.drawRoundedRect(px, py, panel_w, panel_h, 5, 5)

        # Header block
        p.setBrush(QColor(0, 229, 255, int(20 * fade)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(px, py, panel_w, 24, 5, 5)
        f = QFont("Segoe UI", max(6, int(h * 0.032)), QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(QColor(0, 229, 255, int(230 * fade)))
        p.drawText(px + 12, py + 16, "NEXUS AI · ANALYTICS OVERVIEW")

        # 1. Line Chart
        chart_x = px + 12; chart_y = py + 34
        chart_w  = int(panel_w * 0.54); chart_h = int(panel_h * 0.40)
        p.setBrush(QColor(6, 12, 24, int(185 * fade)))
        p.setPen(QPen(QColor(0, 229, 255, int(45 * fade)), 1))
        p.drawRoundedRect(chart_x, chart_y, chart_w, chart_h, 3, 3)

        n = len(self._chart_data)
        pts = []
        for di, val in enumerate(self._chart_data):
            # Dynamic chart line fluctuation when online
            fluct = 0.0
            if sp >= 1.0:
                fluct = 0.05 * math.sin(self._t * 3.5 + di * 1.2)
            val_f = clamp(val + fluct, 0.05, 0.95)
            cx_c = chart_x + int(di * chart_w / (n - 1))
            cy_c = chart_y + chart_h - int(val_f * chart_h * 0.8) - 4
            pts.append(QPointF(cx_c, cy_c))

        path = QPainterPath()
        path.moveTo(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)

        # Glow line
        p.setPen(QPen(QColor(0, 229, 255, int(50 * fade * slide)), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.setPen(QPen(QColor(255, 255, 255, int(230 * fade * slide)), 1.2))
        p.drawPath(path)

        # Bar chart
        bc_x = chart_x + chart_w + 12
        bc_y = chart_y
        bc_w = int(panel_w * 0.32)
        bc_h = chart_h
        p.setBrush(QColor(6, 12, 24, int(185 * fade)))
        p.setPen(QPen(QColor(0, 229, 255, int(45 * fade)), 1))
        p.drawRoundedRect(bc_x, bc_y, bc_w, bc_h, 3, 3)

        bars_data = [("PEOP", 0.80, "#00E5FF"), ("CARS", 0.58, "#3B82F6"),
                     ("PHON", 0.30, "#A78BFA"), ("OTHR", 0.18, "#10B981")]
        bbar_w = int(bc_w * 0.14)
        for bi, (lbl, val, ch) in enumerate(bars_data):
            bx2 = bc_x + 10 + bi * (bbar_w + 10)
            
            # Dynamic bar height fluctuation when online
            fluct = 0.0
            if sp >= 1.0:
                fluct = 0.08 * math.sin(self._t * 4.2 + bi * 1.5)
            val_f = clamp(val + fluct, 0.05, 0.95)
            
            bfill = int(bc_h * 0.7 * val_f * slide)
            col_b = QColor(ch)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(col_b.red(), col_b.green(), col_b.blue(), int(50 * fade)))
            p.drawRect(bx2, bc_y + 8, bbar_w, int(bc_h * 0.7))
            p.setBrush(QColor(col_b.red(), col_b.green(), col_b.blue(), int(200 * fade)))
            p.drawRect(bx2, bc_y + 8 + int(bc_h * 0.7) - bfill, bbar_w, bfill)
            
            f2 = QFont("Courier New", max(5, int(h * 0.025))); p.setFont(f2)
            p.setPen(QColor(148, 163, 184, int(180 * fade)))
            p.drawText(QRectF(bx2 - 4, bc_y + bc_h - 13, bbar_w + 8, 12), Qt.AlignmentFlag.AlignCenter, lbl)

        # 2. Heatmap
        hm_x = chart_x; hm_y = chart_y + chart_h + 10
        hm_w = int(panel_w * 0.54); hm_h = int(panel_h * 0.20)
        p.setBrush(QColor(6, 12, 24, int(185 * fade)))
        p.setPen(QPen(QColor(0, 229, 255, int(45 * fade)), 1))
        p.drawRoundedRect(hm_x, hm_y, hm_w, hm_h, 3, 3)
        
        cell_w = max(2, hm_w // 24)
        for hour in range(24):
            heat = 0.15 + 0.85 * abs(math.sin(hour * 0.45 + 1.2)) * slide
            # Dynamic heat cell fluctuation when online
            if sp >= 1.0:
                heat = clamp(heat + 0.1 * math.sin(self._t * 3.0 + hour * 1.5), 0.05, 0.95)
            r = int(255 * heat); g = int((1.0 - heat) * 200)
            bx3 = hm_x + hour * cell_w
            by3 = hm_y + 8
            p.setBrush(QColor(r, g, int(heat * 60), int(190 * fade)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(bx3, by3, cell_w - 1, hm_h - 11)

        # 3. Realtime Log Widget under the bar chart
        log_x = bc_x; log_y = hm_y; log_w = bc_w; log_h = hm_h
        p.setBrush(QColor(6, 12, 24, int(185 * fade)))
        p.setPen(QPen(QColor(0, 229, 255, int(45 * fade)), 1))
        p.drawRoundedRect(log_x, log_y, log_w, log_h, 3, 3)
        
        p.setPen(QColor(0, 229, 255, int(220 * fade)))
        f_log = QFont("Courier New", max(5, int(h * 0.024)), QFont.Weight.Bold)
        p.setFont(f_log)
        p.drawText(log_x + 8, log_y + 14, "REALTIME ALARM LOG")
        
        log_events = [
            "04:54:02 - CAM01: PERS #12 DET",
            "04:54:08 - CAM01: CAR  #7  DET",
            "04:54:15 - DATABASE DISPATCH",
            "04:54:22 - TELEMETRY SYNCED",
        ]
        for ei, ev in enumerate(log_events):
            p.setPen(QColor(148, 163, 184, int(140 * fade)))
            p.drawText(log_x + 8, log_y + 28 + ei * 12, ev)

    # =========================================================================
    # SCENE 9 – SYSTEM READY
    # =========================================================================
    def _draw_scene9(self, p, w, h, sp, fade):
        t = self._t
        cx, cy = w // 2, h // 2

        self._draw_grid(p, w, h, alpha=int(14 * fade), color=QColor(0, 255, 80))

        # Pulsing radar background rings
        for ri in range(5):
            r_base = int(min(w, h) * (0.12 + ri * 0.12))
            pulse  = 0.9 + 0.1 * math.sin(t * 2.8 + ri * 0.8)
            rr = int(r_base * pulse)
            a  = int(28 * (1.0 - ri / 5) * fade)
            p.setPen(QPen(QColor(0, 229, 255, a), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        # Rotating radar sweep
        sweep = (t * 0.95) % math.tau
        for span in range(45, 0, -5):
            a_val = int(45 * (span / 45) * fade)
            a_angle = sweep - math.radians(span)
            wpath = QPainterPath()
            wpath.moveTo(cx, cy)
            steps = max(2, span // 3)
            for di in range(steps + 1):
                angle = sweep - math.radians(di * span / steps)
                rr = min(w, h) * 0.42
                wpath.lineTo(cx + rr * math.cos(angle), cy + rr * math.sin(angle))
            wpath.closeSubpath()
            p.setBrush(QColor(0, 229, 255, a_val))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(wpath)

        # "SYSTEM READY" big text
        ready_a = int(255 * ease_in_out(clamp(sp * 4, 0, 1)) * fade)
        glow_pulse = 0.8 + 0.2 * math.sin(t * 5.0)
        
        cell_rect = QRectF(0, 0, w, h)
        for offset in [5, 3, 1]:
            f = QFont("Segoe UI", max(10, int(h * 0.13)), QFont.Weight.Bold)
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(2, int(w * 0.015)))
            p.setFont(f)
            p.setPen(QColor(0, 229, 255, int(ready_a * 0.15 * glow_pulse / (offset // 2 + 1))))
            r2 = cell_rect.adjusted(-offset, -int(h * 0.18) - offset, offset, -int(h * 0.18) + offset)
            p.drawText(r2, Qt.AlignmentFlag.AlignCenter, "SYSTEM READY")

        p.setPen(QColor(255, 255, 255, ready_a))
        f = QFont("Segoe UI", max(10, int(h * 0.13)), QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(2, int(w * 0.015)))
        p.setFont(f)
        p.drawText(cell_rect.adjusted(0, -int(h * 0.18), 0, -int(h * 0.18)), Qt.AlignmentFlag.AlignCenter, "SYSTEM READY")

        # Sub-label
        sub_a = int(200 * ease_in_out(clamp((sp - 0.2) * 4, 0, 1)) * fade)
        f2 = QFont("Courier New", max(6, int(h * 0.045)), QFont.Weight.Bold)
        f2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        p.setFont(f2)
        p.setPen(QColor(16, 185, 129, sub_a))
        p.drawText(cell_rect.adjusted(0, int(h * 0.04), 0, int(h * 0.04)), Qt.AlignmentFlag.AlignCenter, "SURVEILLANCE ACTIVE")

        # Indicators pills
        si_a = int(200 * ease_in_out(clamp((sp - 0.4) * 5, 0, 1)) * fade)
        if si_a > 0:
            statuses = [
                ("YOLO11", "#10B981"),
                ("TRACKER", "#10B981"),
                ("MEDIA",   "#10B981"),
            ]
            pill_w = int(w * 0.22)
            gap = int(w * 0.03)
            total_sw = len(statuses) * pill_w + (len(statuses) - 1) * gap
            sx0 = (w - total_sw) // 2
            sy0 = cy + 44
            for si, (slbl, sch) in enumerate(statuses):
                bx = sx0 + si * (pill_w + gap)
                sc_col = QColor(sch); sc_col.setAlpha(si_a)
                p.setBrush(QColor(4, 16, 8, int(150 * fade)))
                p.setPen(QPen(sc_col, 1))
                p.drawRoundedRect(bx, sy0, pill_w, 20, 3, 3)
                
                dot_pulse = 0.5 + 0.5 * math.sin(t * 4 + si)
                p.setBrush(QColor(0, 255, 100, int(si_a * dot_pulse)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(bx + 8, sy0 + 10), 2.5, 2.5)
                
                f3 = QFont("Courier New", max(5, int(h * 0.025)), QFont.Weight.Bold)
                p.setFont(f3)
                p.setPen(sc_col)
                p.drawText(QRectF(bx + 15, sy0, pill_w - 15, 20), Qt.AlignmentFlag.AlignVCenter, slbl)

    # =========================================================================
    # SHARED HELPERS
    # =========================================================================
    def _draw_grid(self, p, w, h, alpha=12, color=None):
        if color is None:
            color = QColor(0, 229, 255, alpha)
        else:
            color.setAlpha(alpha)
        p.setPen(QPen(color, 1))
        sp = 40
        for gx in range(0, int(w), sp):
            p.drawLine(gx, 0, gx, int(h))
        for gy in range(0, int(h), sp):
            p.drawLine(0, gy, int(w), gy)

    def _draw_starfield(self, p, w, h, t, alpha=40):
        rng = random.Random(1984)
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(35):
            sx = rng.randint(0, int(w))
            sy = rng.randint(0, int(h))
            twinkle = 0.4 + 0.6 * math.sin(t * rng.uniform(1.2, 3.5) + rng.random() * 6)
            p.setBrush(QColor(200, 230, 255, int(alpha * twinkle)))
            p.drawEllipse(QPointF(sx, sy), 1, 1)

    def _draw_title(self, p, w, h, alpha, subtitle=""):
        cell_rect = QRectF(0, 0, w, h)
        for offset in [5, 3, 1]:
            f = QFont("Segoe UI", max(10, int(h * 0.13)), QFont.Weight.Bold)
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(2, int(w * 0.015)))
            p.setFont(f)
            p.setPen(QColor(0, 229, 255, int(alpha * 0.16 / (offset // 2 + 1))))
            p.drawText(cell_rect.adjusted(-offset, -int(h * 0.12) - offset,
                                            offset, -int(h * 0.12) + offset),
                       Qt.AlignmentFlag.AlignCenter, "N E X U S")
        
        p.setPen(QColor(255, 255, 255, alpha))
        f = QFont("Segoe UI", max(10, int(h * 0.13)), QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(2, int(w * 0.015)))
        p.setFont(f)
        p.drawText(cell_rect.adjusted(0, -int(h * 0.12), 0, -int(h * 0.12)),
                   Qt.AlignmentFlag.AlignCenter, "N E X U S")

        if subtitle:
            f2 = QFont("Courier New", max(5, int(h * 0.03)))
            f2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
            p.setFont(f2)
            p.setPen(QColor(100, 140, 200, alpha // 2))
            p.drawText(cell_rect.adjusted(0, int(h * 0.04), 0, int(h * 0.04)),
                       Qt.AlignmentFlag.AlignCenter, subtitle)

    def _draw_big_logo(self, p, w, h, alpha, t):
        cx, cy = w // 2, h // 2
        r = min(w, h) * 0.16
        pulse = 0.90 + 0.10 * math.sin(t * 2.5)
        fade = alpha / 255.0
        R = r * pulse

        # ── 0. Radial background energy glow ────────────────────────────────
        energy = QRadialGradient(cx, cy, R * 2.2)
        energy.setColorAt(0.0, QColor(0, 229, 255, int(70 * fade)))
        energy.setColorAt(0.4, QColor(0, 140, 255, int(25 * fade)))
        energy.setColorAt(0.7, QColor(100, 0, 255, int(8 * fade)))
        energy.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(energy))
        p.drawEllipse(QPointF(cx, cy), R * 2.2, R * 2.2)

        # ── 1. Outer target reticle ring (multi-pass glow) ──────────────────
        reticle_r = R * 1.1
        for thick, al in [(4, 20), (2, 60), (1, 180)]:
            p.setPen(QPen(QColor(0, 229, 255, int(al * fade)), thick))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), reticle_r, reticle_r)

        # Crosshair bracket ticks
        tick_len = R * 0.15
        p.setPen(QPen(QColor(0, 229, 255, int(200 * fade)), 1.5))
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
        p.setPen(QPen(QColor(0, 229, 255, int(40 * fade)), 1, Qt.PenStyle.DashLine))
        p.drawEllipse(QPointF(0, 0), orbit_r1, orbit_r2)
        node1_a = t * 2.0
        n1_x = orbit_r1 * math.cos(node1_a)
        n1_y = orbit_r2 * math.sin(node1_a)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 255, 180, int(240 * fade)))
        p.drawEllipse(QPointF(n1_x, n1_y), 3.0, 3.0)
        p.setBrush(QColor(0, 255, 180, int(70 * fade)))
        p.drawEllipse(QPointF(n1_x, n1_y), 7.0, 7.0)
        
        # Orbit 2 (-35 degrees tilt)
        p.rotate(-70)
        p.setPen(QPen(QColor(0, 229, 255, int(40 * fade)), 1, Qt.PenStyle.DashLine))
        p.drawEllipse(QPointF(0, 0), orbit_r1, orbit_r2)
        node2_a = -t * 2.4 + 1.5
        n2_x = orbit_r1 * math.cos(node2_a)
        n2_y = orbit_r2 * math.sin(node2_a)
        p.setBrush(QColor(0, 229, 255, int(240 * fade)))
        p.drawEllipse(QPointF(n2_x, n2_y), 3.0, 3.0)
        p.setBrush(QColor(0, 229, 255, int(70 * fade)))
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
        p.setPen(QPen(QColor(0, 229, 255, int(90 * fade)), 1))
        p.setBrush(QColor(6, 14, 28, int(230 * fade)))
        p.drawPath(core_path)

        # ── 4. Stylized glowing neural mesh "N" ─────────────────────────────
        nr = core_r * 0.65
        v_a = QPointF(cx - nr * 0.55, cy - nr * 0.72)
        v_b = QPointF(cx - nr * 0.55, cy + nr * 0.72)
        v_c = QPointF(cx + nr * 0.55, cy - nr * 0.72)
        v_d = QPointF(cx + nr * 0.55, cy + nr * 0.72)

        p.setBrush(Qt.BrushStyle.NoBrush)
        for thick, al in [(5, 35), (2.5, 90), (1.2, 255)]:
            p.setPen(QPen(QColor(0, 229, 255, int(al * fade)), thick, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawLine(v_a, v_b)
            p.drawLine(v_c, v_d)
            p.drawLine(v_a, v_d)
            
        p.setPen(QPen(QColor(255, 255, 255, int(255 * fade)), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(v_a, v_b)
        p.drawLine(v_c, v_d)
        p.drawLine(v_a, v_d)

        for pt in [v_a, v_b, v_c, v_d]:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 229, 255, int(150 * fade)))
            p.drawEllipse(pt, 4.0, 4.0)
            p.setBrush(QColor(255, 255, 255, int(255 * fade)))
            p.drawEllipse(pt, 1.8, 1.8)

        # ── 5. Expanding radar beacon wave ──────────────────────────────────
        expand_cycle = (t * 0.8) % 1.0
        expand_r = R * (1.1 + 0.65 * expand_cycle)
        expand_a = int(140 * (1.0 - expand_cycle) * fade)
        p.setPen(QPen(QColor(0, 229, 255, expand_a), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), expand_r, expand_r)

        # ── 6. Text Labels ──────────────────────────────────────────────────
        # Title text: "NEXUS AI"
        f_title = QFont("Segoe UI", max(8, int(h * 0.06)), QFont.Weight.Bold)
        f_title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
        p.setFont(f_title)
        p.setPen(QColor(0, 229, 255, int(40 * fade)))
        p.drawText(QRectF(0, cy + r * 1.45 + 1, w, int(h * 0.08)), Qt.AlignmentFlag.AlignCenter, "NEXUS AI")
        p.setPen(QColor(0, 229, 255, alpha))
        p.drawText(QRectF(0, cy + r * 1.45, w, int(h * 0.08)), Qt.AlignmentFlag.AlignCenter, "NEXUS AI")

        # Subtitle
        f_sub = QFont("Segoe UI", max(5, int(h * 0.025)), QFont.Weight.Bold)
        f_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        p.setFont(f_sub)
        p.setPen(QColor(100, 116, 139, int(alpha * 0.8)))
        p.drawText(QRectF(0, cy + r * 1.45 + int(h * 0.06), w, int(h * 0.04)),
                   Qt.AlignmentFlag.AlignCenter, "INTELLIGENT SURVEILLANCE SYSTEM")

    def _draw_status_line(self, p, w, h, text, color):
        f = QFont("Courier New", max(5, int(h * 0.032)), QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(color)
        p.drawText(QRectF(0, h - 22, w, 16), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_brackets(self, p, w, h, fade, scene_idx):
        """Corner HUD brackets on all scenes"""
        bl = 24
        p.setPen(QPen(QColor(0, 229, 255, int(95 * fade)), 1.5))
        p.drawLine(6, 6, 6 + bl, 6);       p.drawLine(6, 6, 6, 6 + bl)
        p.drawLine(w-6, 6, w-6-bl, 6);     p.drawLine(w-6, 6, w-6, 6+bl)
        p.drawLine(6, h-6, 6+bl, h-6);     p.drawLine(6, h-6, 6, h-6-bl)
        p.drawLine(w-6, h-6, w-6-bl, h-6); p.drawLine(w-6, h-6, w-6, h-6-bl)
        
        f = QFont("Courier New", 7)
        p.setFont(f)
        p.setPen(QColor(0, 229, 255, int(70 * fade)))
        ts = f"SCENE {scene_idx + 1}/7 | {self._t:.1f}s / {TOTAL_SEC:.0f}s"
        p.drawText(w - 180, h - 8, ts)
        
        scene_names = [
            "SYSTEM BOOT INITIALIZATION",
            "HOLOGRAPHIC LOGO REVEAL",
            "CAMERA FEED INITIATION",
            "REAL-TIME OBJECT DETECTION",
            "MULTIPLE OBJECT TRACKING SYSTEM",
            "ANALYTICS & METRICS DASHBOARD",
            "SYSTEM DEPLOYMENT READY"
        ]
        p.drawText(10, h - 8, f"NEXUS AI STORYBOARD OVERVIEW | {scene_names[scene_idx]}")

    def _draw_skip_button(self, p, w, h, fade):
        bx = w - 175
        by = h - 40
        bw = 165
        bh = 32
        
        # Draw glassmorphic background
        p.setPen(Qt.PenStyle.NoPen)
        if self._skip_hovered:
            p.setBrush(QColor(12, 35, 70, int(230 * fade)))
        else:
            p.setBrush(QColor(8, 20, 40, int(210 * fade)))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 4, 4)
        
        # Neon Border
        if self._skip_hovered:
            p.setPen(QPen(QColor(255, 255, 255, int(240 * fade)), 1.8))
        else:
            p.setPen(QPen(QColor(0, 229, 255, int(200 * fade)), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 4, 4)
        
        # Text
        f = QFont("Courier New", 8, QFont.Weight.Bold)
        p.setFont(f)
        if self._skip_hovered:
            p.setPen(QColor(255, 255, 255, int(255 * fade)))
        else:
            p.setPen(QColor(0, 229, 255, int(230 * fade)))
        p.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, "SKIP DIAGNOSTICS >")
