import os
import math
import random
import psutil
import sqlite3
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QTableWidget,
    QTableWidgetItem, QLineEdit, QComboBox, QPushButton, QHeaderView,
    QMessageBox, QFileDialog, QFrame, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient, QRadialGradient, QConicalGradient,
    QFont, QBrush, QPainterPath, QFontMetrics,
)


# ---------------------------------------------------------------------------
# TiltCard — glassmorphic card container with 3-D parallax glow
# ---------------------------------------------------------------------------
class TiltCard(QFrame):
    """Futuristic card with mouse tracking that offsets shadows and border highlights in 3D parallax."""

    def __init__(self, glow_color="#00E5FF", parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.glow_color = QColor(glow_color)

        self.mx_offset = 0.0
        self.my_offset = 0.0

        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self.decay_offset)
        self.decay_timer.start(25)

    def mouseMoveEvent(self, event):
        w = self.width()
        h = self.height()
        if w > 0 and h > 0:
            self.mx_offset = (event.position().x() - w / 2) / (w / 2)
            self.my_offset = (event.position().y() - h / 2) / (h / 2)
            self.mx_offset = max(-1.0, min(1.0, self.mx_offset))
            self.my_offset = max(-1.0, min(1.0, self.my_offset))
            self.update()

    def decay_offset(self):
        if not self.underMouse():
            self.mx_offset *= 0.8
            self.my_offset *= 0.8
            if abs(self.mx_offset) < 0.01 and abs(self.my_offset) < 0.01:
                self.mx_offset = 0.0
                self.my_offset = 0.0
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor("transparent"))

        body_rect = self.rect().adjusted(4, 4, -4, -4)

        border_pen = QPen(QColor(255, 255, 255, 20), 1)

        if self.mx_offset != 0.0 or self.my_offset != 0.0:
            gx = int(w / 2 + self.mx_offset * (w / 2))
            gy = int(h / 2 + self.my_offset * (h / 2))

            grad = QLinearGradient(w / 2, h / 2, gx, gy)
            grad.setColorAt(0.0, QColor(255, 255, 255, 20))
            grad.setColorAt(1.0, self.glow_color)
            border_pen = QPen(QBrush(grad), 1.5)

        painter.setPen(border_pen)
        painter.setBrush(QColor(22, 27, 38, 200))
        painter.drawRoundedRect(body_rect, 8, 8)

        if self.mx_offset != 0.0 or self.my_offset != 0.0:
            tag_x = int(w / 2 + self.mx_offset * (w / 2 - 15))
            tag_y = int(h / 2 + self.my_offset * (h / 2 - 15))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.glow_color.red(), self.glow_color.green(), self.glow_color.blue(), 120))
            painter.drawEllipse(QPoint(tag_x, tag_y), 3, 3)

        painter.end()


# ---------------------------------------------------------------------------
# DetectionOverviewWidget — vertical bar chart with QPainter
# ---------------------------------------------------------------------------
class DetectionOverviewWidget(QWidget):
    """Vertical bar chart showing detection counts over recent time windows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self._bars = [0] * 15
        self._total = 0
        self._anim_progress = 1.0

    def set_data(self, bars, total):
        self._bars = list(bars) if bars else [0] * 15
        self._total = total
        self.update()

    def set_anim_progress(self, v):
        self._anim_progress = v
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._bars)
        if n == 0 or w < 40 or h < 40:
            painter.end()
            return

        margin_left = 10
        margin_right = 100
        margin_top = 10
        margin_bottom = 24
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        if chart_w < 20 or chart_h < 20:
            painter.end()
            return

        max_val = max(max(self._bars), 1)

        # Grid lines
        grid_pen = QPen(QColor(255, 255, 255, 13), 1)
        painter.setPen(grid_pen)
        for i in range(5):
            y = margin_top + int(chart_h * i / 4)
            painter.drawLine(margin_left, y, margin_left + chart_w, y)

        # Bars
        bar_gap = 3
        bar_w = max(4, (chart_w - (n - 1) * bar_gap) // n)
        total_bars_w = n * bar_w + (n - 1) * bar_gap
        x_start = margin_left + (chart_w - total_bars_w) // 2

        for i, val in enumerate(self._bars):
            animated_val = val * self._anim_progress
            bar_h = int((animated_val / max_val) * chart_h) if max_val > 0 else 0
            bx = x_start + i * (bar_w + bar_gap)
            by = margin_top + chart_h - bar_h

            grad = QLinearGradient(bx, by, bx, margin_top + chart_h)
            grad.setColorAt(0.0, QColor(0, 229, 255, 220))
            grad.setColorAt(1.0, QColor(0, 229, 255, 60))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), 2, 2)

        # Bottom time labels
        painter.setPen(QColor(148, 163, 184))
        tiny_font = QFont("Segoe UI", 7)
        painter.setFont(tiny_font)
        for i in range(0, n, max(1, n // 5)):
            bx = x_start + i * (bar_w + bar_gap)
            painter.drawText(QRectF(bx - 5, margin_top + chart_h + 2, bar_w + 10, 18),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                             f"-{n - i}")

        # Total badge on the right
        badge_x = w - margin_right + 12
        badge_y = margin_top + chart_h // 2 - 25

        badge_font_big = QFont("Segoe UI", 22, QFont.Weight.Bold)
        badge_font_sm = QFont("Segoe UI", 9, QFont.Weight.Bold)

        displayed_total = int(self._total * self._anim_progress)

        painter.setFont(badge_font_big)
        painter.setPen(QColor(0, 229, 255))
        painter.drawText(QRectF(badge_x, badge_y, margin_right - 20, 36),
                         Qt.AlignmentFlag.AlignCenter, str(displayed_total))

        painter.setFont(badge_font_sm)
        painter.setPen(QColor(148, 163, 184))
        painter.drawText(QRectF(badge_x, badge_y + 34, margin_right - 20, 18),
                         Qt.AlignmentFlag.AlignCenter, "TOTAL")

        painter.end()


# ---------------------------------------------------------------------------
# DonutChartWidget — ring / donut chart with QPainter arcs
# ---------------------------------------------------------------------------
class DonutChartWidget(QWidget):
    """Donut chart with animated arcs and a right-side legend."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self._segments = []  # list of (label, fraction, QColor)
        self._anim_progress = 1.0

    def set_segments(self, segments):
        """segments: list of (label, fraction, QColor)"""
        self._segments = segments
        self.update()

    def set_anim_progress(self, v):
        self._anim_progress = v
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if w < 60 or h < 60 or not self._segments:
            painter.end()
            return

        # Donut geometry — left half
        donut_area = min(w * 0.50, h) - 20
        donut_r = max(30, donut_area / 2)
        cx = 10 + donut_r + 10
        cy = h / 2
        thickness = max(12, donut_r * 0.32)

        outer_r = donut_r
        inner_r = donut_r - thickness
        rect_outer = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
        rect_inner = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

        total_sweep = self._anim_progress * 360.0
        start_angle = 90.0  # start at top

        for label, frac, color in self._segments:
            sweep = frac * total_sweep
            if sweep < 0.5:
                start_angle -= sweep
                continue

            path = QPainterPath()
            path.arcMoveTo(rect_outer, start_angle)
            path.arcTo(rect_outer, start_angle, -sweep)
            path.arcTo(rect_inner, start_angle - sweep, sweep)
            path.closeSubpath()

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawPath(path)

            start_angle -= sweep

        # Center hole fill with background
        painter.setBrush(QColor(22, 27, 38, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect_inner.adjusted(-1, -1, 1, 1))

        # Center text
        center_font = QFont("Segoe UI", max(8, int(inner_r * 0.35)), QFont.Weight.Bold)
        painter.setFont(center_font)
        painter.setPen(QColor(226, 232, 240))
        painter.drawText(rect_inner, Qt.AlignmentFlag.AlignCenter, "DIST")

        # Legend — right side
        legend_x = cx + outer_r + 20
        legend_y_start = max(16, cy - len(self._segments) * 22 / 2)
        label_font = QFont("Segoe UI", 9)
        pct_font = QFont("Segoe UI", 9, QFont.Weight.Bold)

        for i, (label, frac, color) in enumerate(self._segments):
            ly = legend_y_start + i * 22

            # Color dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(legend_x, ly + 2, 10, 10), 2, 2)

            # Label
            painter.setFont(label_font)
            painter.setPen(QColor(148, 163, 184))
            painter.drawText(QRectF(legend_x + 16, ly, 90, 16),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

            # Percentage
            painter.setFont(pct_font)
            painter.setPen(color)
            pct_text = f"{int(frac * 100)}%"
            painter.drawText(QRectF(legend_x + 105, ly, 45, 16),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, pct_text)

        painter.end()


# ---------------------------------------------------------------------------
# ActivityTimelineWidget — 24-hour horizontal bar chart
# ---------------------------------------------------------------------------
class ActivityTimelineWidget(QWidget):
    """Horizontal bar chart for 24h activity timeline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self._bars = [0.0] * 24
        self._anim_progress = 1.0

    def set_data(self, bars):
        self._bars = list(bars) if bars else [0.0] * 24
        self.update()

    def set_anim_progress(self, v):
        self._anim_progress = v
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._bars)
        if n == 0 or w < 40 or h < 40:
            painter.end()
            return

        margin_left = 30
        margin_right = 10
        margin_top = 8
        margin_bottom = 22
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        if chart_w < 20 or chart_h < 20:
            painter.end()
            return

        max_val = max(max(self._bars), 1)

        # Grid lines
        grid_pen = QPen(QColor(255, 255, 255, 13), 1)
        painter.setPen(grid_pen)
        for i in range(5):
            y = margin_top + int(chart_h * i / 4)
            painter.drawLine(margin_left, y, margin_left + chart_w, y)

        # Bars
        bar_gap = 2
        bar_w = max(3, (chart_w - (n - 1) * bar_gap) // n)
        total_bars_w = n * bar_w + (n - 1) * bar_gap
        x_start = margin_left + (chart_w - total_bars_w) // 2

        for i, val in enumerate(self._bars):
            animated_val = val * self._anim_progress
            bar_h = int((animated_val / max_val) * chart_h) if max_val > 0 else 0
            bx = x_start + i * (bar_w + bar_gap)
            by = margin_top + chart_h - bar_h

            grad = QLinearGradient(bx, by, bx, margin_top + chart_h)
            grad.setColorAt(0.0, QColor(245, 158, 11, 230))
            grad.setColorAt(1.0, QColor(245, 158, 11, 50))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), 1.5, 1.5)

        # Hour labels
        painter.setPen(QColor(148, 163, 184))
        tiny_font = QFont("Segoe UI", 7)
        painter.setFont(tiny_font)
        for i in range(0, n, max(1, n // 8)):
            bx = x_start + i * (bar_w + bar_gap)
            painter.drawText(QRectF(bx - 5, margin_top + chart_h + 2, bar_w + 10, 16),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                             f"{i:02d}")

        # Y-axis label
        painter.setPen(QColor(148, 163, 184, 120))
        painter.setFont(QFont("Segoe UI", 7))
        painter.save()
        painter.translate(10, margin_top + chart_h // 2)
        painter.rotate(-90)
        painter.drawText(QRectF(-30, -6, 60, 14), Qt.AlignmentFlag.AlignCenter, "EVENTS")
        painter.restore()

        painter.end()


# ---------------------------------------------------------------------------
# HeatmapWidget — intensity grid drawn with QPainter
# ---------------------------------------------------------------------------
class HeatmapWidget(QWidget):
    """Grid heatmap with colour ramp from dark blue → cyan → green → yellow → red."""

    def __init__(self, rows=8, cols=10, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.rows = rows
        self.cols = cols
        self._data = [[0.0] * cols for _ in range(rows)]
        self._anim_progress = 1.0
        self._randomise_data()

    def _randomise_data(self):
        """Generates simulated heatmap data with organic-looking hot-spots."""
        cx, cy = random.randint(2, self.cols - 3), random.randint(2, self.rows - 3)
        for r in range(self.rows):
            for c in range(self.cols):
                dist = math.sqrt((c - cx) ** 2 + (r - cy) ** 2)
                base = max(0.0, 1.0 - dist / max(self.cols, self.rows))
                self._data[r][c] = min(1.0, base + random.uniform(-0.15, 0.25))

    def evolve(self):
        """Slowly mutate the heatmap data for a living effect."""
        for r in range(self.rows):
            for c in range(self.cols):
                self._data[r][c] += random.uniform(-0.05, 0.05)
                self._data[r][c] = max(0.0, min(1.0, self._data[r][c]))
        self.update()

    def set_anim_progress(self, v):
        self._anim_progress = v
        self.update()

    @staticmethod
    def _intensity_color(t):
        """Map t ∈ [0, 1] → colour ramp: dark navy → cyan → green → yellow → red."""
        t = max(0.0, min(1.0, t))
        stops = [
            (0.00, (10, 20, 50)),
            (0.25, (0, 229, 255)),
            (0.50, (16, 185, 129)),
            (0.75, (245, 200, 11)),
            (1.00, (255, 50, 50)),
        ]
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 != t0 else 0
                r = int(c0[0] + (c1[0] - c0[0]) * f)
                g = int(c0[1] + (c1[1] - c0[1]) * f)
                b = int(c0[2] + (c1[2] - c0[2]) * f)
                return QColor(r, g, b)
        return QColor(255, 50, 50)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad = 8
        avail_w = w - pad * 2
        avail_h = h - pad * 2

        if avail_w < 20 or avail_h < 20:
            painter.end()
            return

        cell_w = avail_w / self.cols
        cell_h = avail_h / self.rows
        gap = 2

        for r in range(self.rows):
            for c in range(self.cols):
                intensity = self._data[r][c] * self._anim_progress
                color = self._intensity_color(intensity)
                rx = pad + c * cell_w + gap / 2
                ry = pad + r * cell_h + gap / 2
                rw = cell_w - gap
                rh = cell_h - gap
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(QRectF(rx, ry, rw, rh), 3, 3)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════
# AnalyticsHub — main 4-panel dashboard + event registry
# ═══════════════════════════════════════════════════════════════════════════
class AnalyticsHub(QWidget):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path

        # Telemetry rolling buffers (kept for API compat)
        self.window_size = 100
        self.latency_buffer = [0.0] * self.window_size
        self.cpu_buffer = [0.0] * self.window_size
        self.ram_buffer = [0.0] * self.window_size
        self.time_steps = list(range(self.window_size))

        # Detection category counters
        self._category_counts = {}
        self._detection_bars = [0] * 15
        self._detection_total = 0

        # Activity timeline (24h buckets)
        self._hourly_activity = [0] * 24

        # Chart animation
        self.chart_anim_scale = 1.0
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_charts_animation)

        self._build_ui()

        # Periodic DB refresh (2 s)
        self.db_timer = QTimer()
        self.db_timer.timeout.connect(self.refresh_database_grid)
        self.db_timer.start(2000)

        # psutil system monitor (1 s)
        self.sys_timer = QTimer()
        self.sys_timer.timeout.connect(self._query_system_telemetry)
        self.sys_timer.start(1000)

        # Heatmap slow evolution (3 s)
        self.heatmap_timer = QTimer()
        self.heatmap_timer.timeout.connect(self._heatmap_widget.evolve)
        self.heatmap_timer.start(3000)

        # Initial data load
        QTimer.singleShot(300, self._load_chart_data_from_db)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        scroll_content.setStyleSheet(self._global_stylesheet())

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(14)

        # ── Top 2x2 chart grid ──────────────────────────────────────────
        chart_grid = QGridLayout()
        chart_grid.setSpacing(14)

        # 1) Detection Overview — top left
        card_detect = TiltCard("#00E5FF")
        cl_detect = QVBoxLayout()
        cl_detect.setContentsMargins(16, 14, 16, 10)
        cl_detect.setSpacing(4)
        lbl_detect = QLabel("DETECTION OVERVIEW")
        lbl_detect.setStyleSheet("font-size:10px; font-weight:bold; color:#00E5FF; letter-spacing:1.5px; background:transparent;")
        cl_detect.addWidget(lbl_detect)
        self._detection_widget = DetectionOverviewWidget()
        self._detection_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        cl_detect.addWidget(self._detection_widget, 1)
        card_detect.setLayout(cl_detect)
        chart_grid.addWidget(card_detect, 0, 0)

        # 2) Object Distribution — top right
        card_donut = TiltCard("#C084FC")
        cl_donut = QVBoxLayout()
        cl_donut.setContentsMargins(16, 14, 16, 10)
        cl_donut.setSpacing(4)
        lbl_donut = QLabel("OBJECT DISTRIBUTION")
        lbl_donut.setStyleSheet("font-size:10px; font-weight:bold; color:#00E5FF; letter-spacing:1.5px; background:transparent;")
        cl_donut.addWidget(lbl_donut)
        self._donut_widget = DonutChartWidget()
        self._donut_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        cl_donut.addWidget(self._donut_widget, 1)
        card_donut.setLayout(cl_donut)
        chart_grid.addWidget(card_donut, 0, 1)

        # 3) Activity Timeline — bottom left
        card_timeline = TiltCard("#F59E0B")
        cl_timeline = QVBoxLayout()
        cl_timeline.setContentsMargins(16, 14, 16, 10)
        cl_timeline.setSpacing(4)
        lbl_timeline = QLabel("ACTIVITY TIMELINE")
        lbl_timeline.setStyleSheet("font-size:10px; font-weight:bold; color:#00E5FF; letter-spacing:1.5px; background:transparent;")
        cl_timeline.addWidget(lbl_timeline)
        self._timeline_widget = ActivityTimelineWidget()
        self._timeline_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        cl_timeline.addWidget(self._timeline_widget, 1)
        card_timeline.setLayout(cl_timeline)
        chart_grid.addWidget(card_timeline, 1, 0)

        # 4) Heatmap — bottom right
        card_heatmap = TiltCard("#10B981")
        cl_heatmap = QVBoxLayout()
        cl_heatmap.setContentsMargins(16, 14, 16, 10)
        cl_heatmap.setSpacing(4)
        lbl_heatmap = QLabel("HEATMAP")
        lbl_heatmap.setStyleSheet("font-size:10px; font-weight:bold; color:#00E5FF; letter-spacing:1.5px; background:transparent;")
        cl_heatmap.addWidget(lbl_heatmap)
        self._heatmap_widget = HeatmapWidget(rows=8, cols=10)
        self._heatmap_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        cl_heatmap.addWidget(self._heatmap_widget, 1)
        card_heatmap.setLayout(cl_heatmap)
        chart_grid.addWidget(card_heatmap, 1, 1)

        content_layout.addLayout(chart_grid, 3)

        # ── Bottom: Event Registry ──────────────────────────────────────
        box_registry = TiltCard("#00E5FF")
        box_registry.setObjectName("box_registry")
        reg_layout = QVBoxLayout()
        reg_layout.setContentsMargins(20, 20, 20, 20)
        reg_layout.setSpacing(12)

        reg_title = QLabel("NEXUS PERSISTENT EVENT REGISTRY")
        reg_title.setStyleSheet("font-size:10px; font-weight:bold; color:#00E5FF; letter-spacing:1.5px; background:transparent;")
        reg_layout.addWidget(reg_title)

        # Filters bar
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Category/ID...")
        self.search_input.textChanged.connect(self.filter_database_registry)
        filters_layout.addWidget(self.search_input, 1)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        try:
            from core.engine import TARGET_CLASSES
            self.category_filter.addItems(sorted(list(set(TARGET_CLASSES.values()))))
        except Exception:
            pass
        self.category_filter.currentIndexChanged.connect(self.filter_database_registry)
        filters_layout.addWidget(self.category_filter)

        self.refresh_btn = QPushButton("Refresh Table")
        self.refresh_btn.clicked.connect(self.refresh_database_grid)
        filters_layout.addWidget(self.refresh_btn)

        reg_layout.addLayout(filters_layout)

        # Table
        self.table_view = QTableWidget()
        self.table_view.setColumnCount(5)
        self.table_view.setHorizontalHeaderLabels(["ID", "Timestamp", "Category", "Tracking ID", "Confidence"])
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        reg_layout.addWidget(self.table_view, 1)

        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.export_btn = QPushButton("EXPORT EXCEL/CSV REPORT")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.clicked.connect(self.export_registry_to_csv)
        actions_layout.addWidget(self.export_btn, 1)

        self.export_html_btn = QPushButton("EXPORT EXECUTIVE HTML REPORT")
        self.export_html_btn.setObjectName("export_btn")
        self.export_html_btn.clicked.connect(self.export_registry_to_html)
        actions_layout.addWidget(self.export_html_btn, 1)

        self.clear_btn = QPushButton("WIPE REGISTRY")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.clicked.connect(self.wipe_registry_db)
        actions_layout.addWidget(self.clear_btn, 1)

        reg_layout.addLayout(actions_layout)
        box_registry.setLayout(reg_layout)

        content_layout.addWidget(box_registry, 2)

        scroll_content.setLayout(content_layout)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    # ------------------------------------------------------------------
    # Global QSS
    # ------------------------------------------------------------------
    @staticmethod
    def _global_stylesheet():
        return """
            QWidget {
                background-color: transparent;
                color: #e2e8f0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame#box_registry {
                background-color: transparent;
                border: none;
            }
            QLabel {
                color: #94a3b8;
                font-size: 13px;
                background-color: transparent;
            }
            QLineEdit, QComboBox {
                background-color: rgba(11, 15, 25, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 0 10px;
                color: #f8fafc;
                min-width: 140px;
                min-height: 32px;
                max-height: 32px;
            }
            QLineEdit:focus, QComboBox:hover {
                border: 1px solid #00E5FF;
            }
            QPushButton {
                background-color: rgba(30, 41, 59, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: white;
                border-radius: 5px;
                padding: 0 15px;
                font-weight: bold;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                border: 1px solid #00E5FF;
            }
            QPushButton#export_btn {
                background-color: #00E5FF;
                color: #0B0F19;
                border: none;
            }
            QPushButton#export_btn:hover {
                background-color: #00B4D8;
            }
            QPushButton#clear_btn {
                background-color: #FF003C;
                color: white;
                border: none;
            }
            QPushButton#clear_btn:hover {
                background-color: #CC0030;
            }
            QTableView {
                background-color: rgba(11, 15, 25, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #f8fafc;
                gridline-color: rgba(255, 255, 255, 0.04);
            }
            QHeaderView::section {
                background-color: #161B26;
                color: #f8fafc;
                padding: 6px;
                border: 1px solid rgba(255, 255, 255, 0.04);
                font-weight: bold;
            }
        """

    # ------------------------------------------------------------------
    # Data loading from SQLite → chart widgets
    # ------------------------------------------------------------------
    def _load_chart_data_from_db(self):
        """Query the DB to populate category counts, detection bars, hourly timeline."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            # Category distribution
            cursor.execute("SELECT object_name, COUNT(*) FROM event_logs GROUP BY object_name")
            rows = cursor.fetchall()
            self._category_counts = {}
            for name, cnt in rows:
                key = str(name).upper()
                self._category_counts[key] = self._category_counts.get(key, 0) + cnt

            # Total
            self._detection_total = sum(self._category_counts.values())

            # Recent detection bars (last 15 'windows' — group by minute or by rowid chunks)
            cursor.execute("SELECT COUNT(*) FROM event_logs")
            total_rows = cursor.fetchone()[0]
            n_bars = 15
            self._detection_bars = [0] * n_bars
            if total_rows > 0:
                chunk = max(1, total_rows // n_bars)
                cursor.execute("SELECT id FROM event_logs ORDER BY id ASC")
                all_ids = [r[0] for r in cursor.fetchall()]
                for i in range(n_bars):
                    start_idx = i * chunk
                    end_idx = min((i + 1) * chunk, len(all_ids))
                    self._detection_bars[i] = max(0, end_idx - start_idx)

            # Hourly activity from timestamps
            self._hourly_activity = [0] * 24
            cursor.execute("SELECT timestamp FROM event_logs")
            for (ts,) in cursor.fetchall():
                try:
                    ts_str = str(ts)
                    # Expecting format like "2025-01-15 14:22:33" or ISO
                    if " " in ts_str and ":" in ts_str:
                        hour_part = ts_str.split(" ")[1].split(":")[0]
                        hour = int(hour_part)
                        if 0 <= hour < 24:
                            self._hourly_activity[hour] += 1
                except Exception:
                    pass

            conn.close()
        except Exception as e:
            print(f"[AnalyticsHub] Chart data load failed: {e}")

        self._push_data_to_widgets()

    def _push_data_to_widgets(self):
        """Send computed data arrays to the chart widgets."""
        # Detection bar chart
        self._detection_widget.set_data(self._detection_bars, self._detection_total)

        # Donut chart — build segments
        color_map = {
            "PERSON": QColor(0, 229, 255),       # cyan
            "VEHICLE": QColor(192, 132, 252),     # purple
            "PHONE": QColor(16, 185, 129),        # green
        }
        default_color = QColor(245, 158, 11)       # amber for OTHER / unknown

        segments = []
        total = max(self._detection_total, 1)
        assigned = {}
        other_count = 0

        for cat, cnt in sorted(self._category_counts.items(), key=lambda x: -x[1]):
            if cat in color_map:
                assigned[cat] = cnt
            else:
                other_count += cnt

        for cat in ["PERSON", "VEHICLE", "PHONE"]:
            cnt = assigned.get(cat, 0)
            if cnt > 0 or cat == "PERSON":
                segments.append((cat, cnt / total, color_map[cat]))

        if other_count > 0 or not segments:
            segments.append(("OTHER", max(other_count, 0) / total if total > 0 else 0.25, default_color))

        # Guarantee at least some visual if DB is empty
        if self._detection_total == 0:
            segments = [
                ("PERSON", 0.68, QColor(0, 229, 255)),
                ("VEHICLE", 0.18, QColor(192, 132, 252)),
                ("PHONE", 0.07, QColor(16, 185, 129)),
                ("OTHER", 0.07, QColor(245, 158, 11)),
            ]

        self._donut_widget.set_segments(segments)

        # Activity timeline
        self._timeline_widget.set_data(self._hourly_activity)

    # ------------------------------------------------------------------
    # Public API — chart animation
    # ------------------------------------------------------------------
    def trigger_charts_animation(self):
        """Initializes scale-up growth animation for all chart panels."""
        self.chart_anim_scale = 0.0
        self._detection_widget.set_anim_progress(0.0)
        self._donut_widget.set_anim_progress(0.0)
        self._timeline_widget.set_anim_progress(0.0)
        self._heatmap_widget.set_anim_progress(0.0)
        self.anim_timer.stop()
        self.anim_timer.start(30)

    def _update_charts_animation(self):
        self.chart_anim_scale += 0.06
        if self.chart_anim_scale >= 1.0:
            self.chart_anim_scale = 1.0
            self.anim_timer.stop()

        p = self.chart_anim_scale
        # Ease-out cubic
        ep = 1.0 - (1.0 - p) ** 3

        self._detection_widget.set_anim_progress(ep)
        self._donut_widget.set_anim_progress(ep)
        self._timeline_widget.set_anim_progress(ep)
        self._heatmap_widget.set_anim_progress(ep)

    # ------------------------------------------------------------------
    # Public API — live latency feed
    # ------------------------------------------------------------------
    def feed_live_latency(self, latency_ms):
        """Called by the inference thread to feed latest execution latency."""
        self.latency_buffer.pop(0)
        self.latency_buffer.append(latency_ms)

    # ------------------------------------------------------------------
    # System telemetry (private)
    # ------------------------------------------------------------------
    def _query_system_telemetry(self):
        """Timer callback to fetch psutil footprints."""
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        self.cpu_buffer.pop(0)
        self.cpu_buffer.append(cpu)

        self.ram_buffer.pop(0)
        self.ram_buffer.append(ram)

    # ------------------------------------------------------------------
    # Public API — database / registry
    # ------------------------------------------------------------------
    def refresh_database_grid(self):
        """Queries the SQLite database and populates the logs table."""
        search_term = self.search_input.text().strip()
        category = self.category_filter.currentText()

        query = "SELECT id, timestamp, object_name, tracking_id, confidence FROM event_logs WHERE 1=1"
        params = []

        if category != "All Categories":
            query += " AND object_name = ?"
            params.append(category.lower())

        if search_term:
            query += " AND (object_name LIKE ? OR CAST(tracking_id AS TEXT) LIKE ?)"
            params.append(f"%{search_term}%")
            params.append(f"%{search_term}%")

        query += " ORDER BY timestamp DESC LIMIT 500"

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            self.table_view.setSortingEnabled(False)
            self.table_view.setRowCount(0)

            for row_idx, row in enumerate(rows):
                self.table_view.insertRow(row_idx)
                for col_idx, val in enumerate(row):
                    if col_idx == 4:
                        val_str = f"{int(float(val) * 100)}%"
                    elif col_idx == 2:
                        val_str = str(val).upper()
                    else:
                        val_str = str(val)
                    item = QTableWidgetItem(val_str)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table_view.setItem(row_idx, col_idx, item)

            self.table_view.setSortingEnabled(True)
        except Exception as e:
            print(f"[AnalyticsHub] Database query failed: {e}")

        # Refresh chart data too
        self._load_chart_data_from_db()

    def filter_database_registry(self):
        """Callback for when search text or category changes."""
        self.refresh_database_grid()

    def export_registry_to_csv(self):
        """Exports the SQLite database registry directly into a CSV file format."""
        import csv
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
        os.makedirs(export_dir, exist_ok=True)

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Surveillance Report",
            os.path.join(export_dir, "surveillance_registry.csv"),
            "CSV Files (*.csv)"
        )

        if not filepath:
            return

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_logs ORDER BY timestamp DESC")
            rows = cursor.fetchall()

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Timestamp", "Category", "Tracking ID", "Confidence"])
                writer.writerows(rows)

            conn.close()
            QMessageBox.information(self, "Export Status", f"Database Registry successfully exported to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Failed to export registry: {e}")

    def wipe_registry_db(self):
        """Wipes the database table."""
        reply = QMessageBox.question(
            self, "System Wipe Confirmation",
            "WARNING: This will permanently wipe all SQLite tracking logs. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM event_logs")
                conn.commit()
                conn.close()
                self.refresh_database_grid()
                QMessageBox.information(self, "System Wipe", "Database Registry successfully cleared.")
            except Exception as e:
                QMessageBox.critical(self, "Wipe Failure", f"Failed to wipe registry: {e}")

    def export_registry_to_html(self):
        """Generates a styled HTML Executive Summary Report from the SQLite database."""
        from database.reporter import Reporter
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
        os.makedirs(export_dir, exist_ok=True)

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Executive Report",
            os.path.join(export_dir, "surveillance_executive_report.html"),
            "HTML Files (*.html)"
        )

        if not filepath:
            return

        if Reporter.export_events_to_html(self.db_path, filepath):
            QMessageBox.information(self, "Export Status", f"Executive Report successfully generated at:\n{filepath}")
        else:
            QMessageBox.critical(self, "Export Failure", "Failed to generate Executive Report.")
