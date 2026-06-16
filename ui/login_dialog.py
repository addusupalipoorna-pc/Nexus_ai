import math
import random
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                              QPushButton, QFrame, QCheckBox, QStackedWidget, QWidget)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (QPainter, QColor, QPen, QRadialGradient, QBrush, QPainterPath,
                          QFont, QLinearGradient)
from database.logger import DatabaseLogger


# ─────────────────────────────────────────────────────────────
#  Animated Hexagonal Logo Widget
# ─────────────────────────────────────────────────────────────
class _HexLogoWidget(QWidget):
    """Custom-painted animated Neural Mesh logo widget matching the NEXUS AI theme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.tick = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(25)

    def _tick(self):
        self.tick += 0.025
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = 26.0
        pulse = 0.90 + 0.10 * math.sin(self.tick * 2.5)
        R = r * pulse
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

        # Crosshair bracket ticks
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

        p.end()


# ─────────────────────────────────────────────────────────────
#  Drifting Particle (data class)
# ─────────────────────────────────────────────────────────────
class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "r")

    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = random.uniform(-0.25, 0.25)
        self.vy = random.uniform(-0.25, 0.25)
        self.r = random.uniform(1.0, 2.0)

    def move(self, w, h):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0:
            self.x = w
        elif self.x > w:
            self.x = 0
        if self.y < 0:
            self.y = h
        elif self.y > h:
            self.y = 0


# ─────────────────────────────────────────────────────────────
#  Login Dialog
# ─────────────────────────────────────────────────────────────
class LoginDialog(QDialog):
    """Premium cyberpunk authentication dialog with animated logo,
    particle background, and login / sign-up tabs."""

    def __init__(self, db_logger: DatabaseLogger, parent=None):
        super().__init__(parent)
        self.db = db_logger
        self.authenticated = False

        # ── window flags ────────────────────────────────────────────
        self.setWindowTitle("NEXUS AI // SECURE LOGIN")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(440, 580)

        # ── particles ───────────────────────────────────────────────
        self._particles = [_Particle(440, 580) for _ in range(18)]
        self._particle_timer = QTimer(self)
        self._particle_timer.timeout.connect(self._tick_particles)
        self._particle_timer.start(33)

        # ── dragging support (frameless) ────────────────────────────
        self._drag_pos = None

        # ── build UI ────────────────────────────────────────────────
        self._build_ui()

    # =================================================================
    #  PARTICLES
    # =================================================================
    def _tick_particles(self):
        w, h = self.width(), self.height()
        for pt in self._particles:
            pt.move(w, h)
        self.update()

    # =================================================================
    #  PAINT – draw particles + connections behind everything
    # =================================================================
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # card background (rounded rect)
        rect = self.rect().adjusted(6, 6, -6, -6)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 14, 14)
        p.setPen(QPen(QColor(0, 229, 255, 128), 2))
        p.setBrush(QColor(10, 14, 26, 245))
        p.drawPath(path)

        # particle dots + connections
        conn_dist = 100.0
        dot_color = QColor(0, 229, 255, 55)
        line_color = QColor(0, 229, 255)
        for i, a in enumerate(self._particles):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot_color)
            p.drawEllipse(QPointF(a.x, a.y), a.r, a.r)
            for b in self._particles[i + 1:]:
                dx = a.x - b.x
                dy = a.y - b.y
                d = math.sqrt(dx * dx + dy * dy)
                if d < conn_dist:
                    alpha = int(40 * (1 - d / conn_dist))
                    lc = QColor(line_color)
                    lc.setAlpha(alpha)
                    p.setPen(QPen(lc, 0.6))
                    p.drawLine(QPointF(a.x, a.y), QPointF(b.x, b.y))

        p.end()

    # =================================================================
    #  DRAG SUPPORT (frameless window)
    # =================================================================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # =================================================================
    #  UI BUILDER
    # =================================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(0)

        # ── close button ────────────────────────────────────────────
        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #64748b; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { color: #FF003C; }
        """)
        btn_close.clicked.connect(self.reject)
        close_row.addWidget(btn_close)
        root.addLayout(close_row)

        # ── logo ────────────────────────────────────────────────────
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo = _HexLogoWidget()
        logo_row.addWidget(self._logo)
        root.addLayout(logo_row)

        # ── title / subtitle ────────────────────────────────────────
        title = QLabel("NEXUS AI")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:#00E5FF; font-size:22px; font-weight:bold;"
            "letter-spacing:3px; background:transparent; margin-top:4px;"
        )
        root.addWidget(title)

        subtitle = QLabel("INTELLIGENT SURVEILLANCE SYSTEM")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "color:#64748b; font-size:9px; font-weight:bold;"
            "letter-spacing:2px; background:transparent; margin-bottom:12px;"
        )
        root.addWidget(subtitle)

        # ── tab buttons ─────────────────────────────────────────────
        tab_row = QHBoxLayout()
        tab_row.setSpacing(0)
        self._btn_tab_login = QPushButton("LOGIN")
        self._btn_tab_signup = QPushButton("SIGN UP")
        for btn in (self._btn_tab_login, self._btn_tab_signup):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(34)
        tab_row.addWidget(self._btn_tab_login)
        tab_row.addWidget(self._btn_tab_signup)
        root.addLayout(tab_row)

        root.addSpacing(6)

        # ── stacked pages ───────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:transparent;")
        self._stack.addWidget(self._build_login_page())
        self._stack.addWidget(self._build_signup_page())
        root.addWidget(self._stack, 1)

        # ── error / status label ────────────────────────────────────
        self._error_label = QLabel("")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            "color:#FF003C; font-size:11px; font-weight:bold;"
            "background:transparent; margin-top:6px;"
        )
        root.addWidget(self._error_label)

        root.addStretch()

        # ── connect tabs ────────────────────────────────────────────
        self._btn_tab_login.clicked.connect(lambda: self._switch_tab(0))
        self._btn_tab_signup.clicked.connect(lambda: self._switch_tab(1))
        self._switch_tab(0)

    # -----------------------------------------------------------------
    #  Tab switching
    # -----------------------------------------------------------------
    _TAB_ACTIVE_SS = (
        "QPushButton { background:transparent; border:none;"
        "border-bottom:2px solid #00E5FF; color:#00E5FF;"
        "font-size:13px; font-weight:bold; letter-spacing:1px; padding-bottom:4px; }"
    )
    _TAB_INACTIVE_SS = (
        "QPushButton { background:transparent; border:none;"
        "border-bottom:2px solid transparent; color:#64748b;"
        "font-size:13px; font-weight:bold; letter-spacing:1px; padding-bottom:4px; }"
        "QPushButton:hover { color:#94a3b8; }"
    )

    def _switch_tab(self, index: int):
        self._stack.setCurrentIndex(index)
        self._error_label.setText("")
        if index == 0:
            self._btn_tab_login.setStyleSheet(self._TAB_ACTIVE_SS)
            self._btn_tab_signup.setStyleSheet(self._TAB_INACTIVE_SS)
        else:
            self._btn_tab_login.setStyleSheet(self._TAB_INACTIVE_SS)
            self._btn_tab_signup.setStyleSheet(self._TAB_ACTIVE_SS)

    # -----------------------------------------------------------------
    #  Shared stylesheet fragments
    # -----------------------------------------------------------------
    _INPUT_SS = """
        QLineEdit {
            background-color: #0B0F19;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px;
            padding: 12px;
            color: #f8fafc;
            font-size: 13px;
        }
        QLineEdit:focus {
            border: 1px solid #00E5FF;
        }
    """
    _LABEL_SS = (
        "color:#94a3b8; font-size:11px; font-weight:bold;"
        "letter-spacing:1px; background:transparent; margin-top:6px;"
    )

    # -----------------------------------------------------------------
    #  Login page
    # -----------------------------------------------------------------
    def _build_login_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 4, 10, 0)
        lay.setSpacing(4)

        lay.addWidget(self._make_label("OPERATOR USERNAME"))
        self._login_user = QLineEdit()
        self._login_user.setPlaceholderText("Enter operator username…")
        self._login_user.setStyleSheet(self._INPUT_SS)
        lay.addWidget(self._login_user)

        lay.addWidget(self._make_label("PASSKEY IDENTIFIER"))
        self._login_pass = QLineEdit()
        self._login_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._login_pass.setPlaceholderText("Enter passkey identifier…")
        self._login_pass.setStyleSheet(self._INPUT_SS)
        self._login_pass.returnPressed.connect(self._attempt_login)
        lay.addWidget(self._login_pass)

        # remember-me checkbox
        self._remember_cb = QCheckBox("Remember Me")
        self._remember_cb.setStyleSheet("""
            QCheckBox {
                color: #94a3b8; font-size: 11px; font-weight: bold;
                background: transparent; spacing: 6px; margin-top: 4px;
            }
            QCheckBox::indicator {
                width: 14px; height: 14px;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 3px;
                background: #0B0F19;
            }
            QCheckBox::indicator:checked {
                background: #00E5FF;
                border-color: #00E5FF;
            }
        """)
        lay.addWidget(self._remember_cb)

        lay.addSpacing(8)

        btn_auth = QPushButton("AUTHENTICATE")
        btn_auth.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_auth.setFixedHeight(44)
        btn_auth.setStyleSheet("""
            QPushButton {
                background-color: #00E5FF; color: #0B0F19; border: none;
                border-radius: 6px; padding: 12px; font-weight: bold;
                font-size: 14px; letter-spacing: 1px;
            }
            QPushButton:hover { background-color: #00B4D8; }
        """)
        btn_auth.clicked.connect(self._attempt_login)
        lay.addWidget(btn_auth)

        lay.addStretch()
        return page

    # -----------------------------------------------------------------
    #  Sign-up page
    # -----------------------------------------------------------------
    def _build_signup_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(10, 4, 10, 0)
        lay.setSpacing(4)

        lay.addWidget(self._make_label("CHOOSE USERNAME"))
        self._reg_user = QLineEdit()
        self._reg_user.setPlaceholderText("Choose operator username…")
        self._reg_user.setStyleSheet(self._INPUT_SS)
        lay.addWidget(self._reg_user)

        lay.addWidget(self._make_label("CREATE PASSKEY"))
        self._reg_pass = QLineEdit()
        self._reg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._reg_pass.setPlaceholderText("Create passkey identifier…")
        self._reg_pass.setStyleSheet(self._INPUT_SS)
        lay.addWidget(self._reg_pass)

        lay.addWidget(self._make_label("CONFIRM PASSKEY"))
        self._reg_pass2 = QLineEdit()
        self._reg_pass2.setEchoMode(QLineEdit.EchoMode.Password)
        self._reg_pass2.setPlaceholderText("Re-enter passkey identifier…")
        self._reg_pass2.setStyleSheet(self._INPUT_SS)
        self._reg_pass2.returnPressed.connect(self._attempt_register)
        lay.addWidget(self._reg_pass2)

        lay.addSpacing(8)

        btn_reg = QPushButton("REGISTER OPERATOR")
        btn_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reg.setFixedHeight(44)
        btn_reg.setStyleSheet("""
            QPushButton {
                background: transparent; color: #00E5FF;
                border: 2px solid #00E5FF; border-radius: 6px;
                padding: 12px; font-weight: bold; font-size: 14px;
                letter-spacing: 1px;
            }
            QPushButton:hover { background: rgba(0,229,255,0.1); }
        """)
        btn_reg.clicked.connect(self._attempt_register)
        lay.addWidget(btn_reg)

        lay.addStretch()
        return page

    # -----------------------------------------------------------------
    #  Helpers
    # -----------------------------------------------------------------
    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(self._LABEL_SS)
        return lbl

    def _show_error(self, msg: str):
        self._error_label.setStyleSheet(
            "color:#FF003C; font-size:11px; font-weight:bold;"
            "background:transparent; margin-top:6px;"
        )
        self._error_label.setText(msg)

    def _show_success(self, msg: str):
        self._error_label.setStyleSheet(
            "color:#10B981; font-size:11px; font-weight:bold;"
            "background:transparent; margin-top:6px;"
        )
        self._error_label.setText(msg)

    # -----------------------------------------------------------------
    #  Authentication logic
    # -----------------------------------------------------------------
    def _attempt_login(self):
        username = self._login_user.text().strip()
        password = self._login_pass.text()

        if not username or not password:
            self._show_error("⚠  Enter username and password.")
            return

        if self.db.verify_user(username, password):
            self.authenticated = True
            self.accept()
        else:
            self._show_error("⛔  ACCESS DENIED — Invalid credentials.")

    def _attempt_register(self):
        username = self._reg_user.text().strip()
        password = self._reg_pass.text()
        confirm = self._reg_pass2.text()

        if not username or not password or not confirm:
            self._show_error("⚠  All fields are required.")
            return

        if len(username) < 3:
            self._show_error("⚠  Username must be at least 3 characters.")
            return

        if len(password) < 4:
            self._show_error("⚠  Passkey must be at least 4 characters.")
            return

        if password != confirm:
            self._show_error("⚠  Passkeys do not match.")
            return

        if self.db.register_user(username, password):
            self._show_success("✔  Operator registered. You may now log in.")
            # auto-switch to login tab after short delay
            QTimer.singleShot(1200, lambda: self._switch_tab(0))
        else:
            self._show_error("⛔  Registration failed — username may already exist.")
