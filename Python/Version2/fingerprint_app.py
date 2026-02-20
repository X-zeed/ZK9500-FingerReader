from custom_dialog import Dialog
import sys, re, subprocess, os, time
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QStackedWidget, QFrame, QMessageBox,
    QGraphicsDropShadowEffect, QSizePolicy, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSpacerItem, QGridLayout, QScrollArea
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QRect, QPoint,
    QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QConicalGradient,
    QFontDatabase, QPixmap, QIcon, QPainterPath, QPolygon
)

load_dotenv()

# ══════════════════════════════════════════════════════════════
# PALETTE — Clean Light
# ══════════════════════════════════════════════════════════════
C = {
    "bg":          "#F4F6F9",
    "surface":     "#FFFFFF",
    "panel":       "#EAECF0",
    "card":        "#FFFFFF",
    "elevated":    "#F0F2F5",
    "border":      "#D8DCE3",
    "border_hi":   "#B0B8C8",
    "cyan":        "#1565C0",   # primary blue
    "cyan_dim":    "#5E92D2",
    "cyan_glow":   "#E3EDF8",
    "amber":       "#E65100",   # warning orange
    "amber_dim":   "#F09060",
    "amber_glow":  "#FFF3EC",
    "green":       "#2E7D32",   # success green
    "green_dim":   "#6AAF6E",
    "green_glow":  "#EDF7ED",
    "red":         "#C62828",   # danger red
    "red_dim":     "#E07070",
    "red_glow":    "#FDECEA",
    "text":        "#1A2033",
    "text_dim":    "#5A6478",
    "text_muted":  "#9AA3B4",
    "text_hi":     "#0D1117",
    "grid":        "#F0F2F5",
}

FONT_MONO = "Consolas"
FONT_UI   = "Segoe UI"


# ══════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )

def is_base64(s):
    return re.fullmatch(r'[A-Za-z0-9+/=]+', s) is not None

def extract_template(output):
    for line in reversed(output.strip().splitlines()):
        l = line.strip()
        if len(l) > 100 and is_base64(l):
            return l
    return None


# ══════════════════════════════════════════════════════════════
# WORKER THREADS
# ══════════════════════════════════════════════════════════════
class ScanWorker(QThread):
    captured = pyqtSignal(str)
    failed   = pyqtSignal(str)

    def run(self):
        try:
            r = subprocess.run(["Application/save.exe"], capture_output=True, text=True, timeout=15)
            t = extract_template(r.stdout)
            if t:
                self.captured.emit(t)
            else:
                self.failed.emit("ไม่พบ Template — วางนิ้วใหม่อีกครั้ง")
        except Exception as e:
            self.failed.emit(str(e))


class VerifyWorker(QThread):
    matched  = pyqtSignal(str)
    no_match = pyqtSignal()
    progress = pyqtSignal(str)
    error    = pyqtSignal(str)

    def run(self):
        try:
            r = subprocess.run(["Application/verify.exe"], capture_output=True, text=True, timeout=15)
            scan = extract_template(r.stdout)
            if not scan:
                self.no_match.emit()
                return
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("SELECT user_id, template FROM fingerprints")
            rows = cur.fetchall()
            cur.close(); conn.close()
            self.progress.emit(f"กำลังตรวจสอบ {len(rows)} รายการ...")
            for uid, dbt in rows:
                db_b64 = bytes(dbt).decode()
                cmp = subprocess.run(
                    ["Application/compare.exe", scan, db_b64],
                    capture_output=True, text=True)
                try:
                    if int(cmp.stdout.strip()) > 60:
                        self.matched.emit(str(uid))
                        return
                except:
                    continue
            self.no_match.emit()
        except Exception as e:
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════
# CUSTOM WIDGETS
# ══════════════════════════════════════════════════════════════
class ScannerRing(QWidget):
    """Animated fingerprint scanner ring — HMI style."""

    def __init__(self, size=200, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._state  = "idle"
        self._angle  = 0
        self._pulse  = 0.0
        self._ripple = []
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_state(self, state):
        self._state = state
        if state == "scanning":
            self._ripple.clear()
        self.update()

    def _tick(self):
        self._angle = (self._angle + 2) % 360
        self._pulse = (self._pulse + 0.04) % (2 * 3.14159)
        new_ripple  = []
        for r, a in self._ripple:
            if a > 4:
                new_ripple.append((r + 1.5, a - 4))
        if self._state == "scanning" and len(self._ripple) < 4:
            import math
            if int(self._pulse * 10) % 15 == 0:
                new_ripple.append((0, 255))
        self._ripple = new_ripple
        if self._state in ("scanning",):
            self.update()

    def paintEvent(self, event):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h   = self.width(), self.height()
        cx, cy = w / 2, h / 2
        R      = w / 2 - 6

        if   self._state == "success":  c_main = QColor(C["green"]); c_glow = QColor(C["green_glow"])
        elif self._state == "fail":     c_main = QColor(C["red"]);   c_glow = QColor(C["red_glow"])
        elif self._state == "scanning": c_main = QColor(C["cyan"]);  c_glow = QColor(C["cyan_glow"])
        elif self._state == "ready":    c_main = QColor(C["amber"]); c_glow = QColor(C["amber_glow"])
        else:                           c_main = QColor(C["border_hi"]); c_glow = QColor(C["bg"])

        # glow background
        grad = QRadialGradient(cx, cy, R)
        g1   = QColor(c_main); g1.setAlpha(30 if self._state != "idle" else 0)
        grad.setColorAt(0.4, g1)
        grad.setColorAt(1.0, QColor(Qt.transparent))
        p.setPen(Qt.NoPen); p.setBrush(grad)
        p.drawEllipse(int(cx - R), int(cy - R), int(R * 2), int(R * 2))

        # ripple rings
        for radius, alpha in self._ripple:
            rc = QColor(c_main); rc.setAlpha(int(alpha))
            p.setPen(QPen(rc, 1.5)); p.setBrush(Qt.NoBrush)
            rr = R * 0.4 + radius
            p.drawEllipse(int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2))

        # outer track
        p.setPen(QPen(QColor(C["border"]), 3)); p.setBrush(Qt.NoBrush)
        p.drawEllipse(int(cx - R), int(cy - R), int(R * 2), int(R * 2))

        if self._state == "scanning":
            sweep   = 110
            pen_arc = QPen(c_main, 4); pen_arc.setCapStyle(Qt.RoundCap)
            p.setPen(pen_arc)
            p.drawArc(int(cx - R), int(cy - R), int(R * 2), int(R * 2),
                      self._angle * 16, sweep * 16)
            c_trail = QColor(c_main); c_trail.setAlpha(60)
            pen_t   = QPen(c_trail, 2); pen_t.setCapStyle(Qt.RoundCap)
            p.setPen(pen_t)
            p.drawArc(int(cx - R), int(cy - R), int(R * 2), int(R * 2),
                      (self._angle + sweep) * 16, 80 * 16)
        else:
            p.setPen(QPen(c_main, 3 if self._state == "idle" else 4))
            p.drawEllipse(int(cx - R), int(cy - R), int(R * 2), int(R * 2))

        # inner disc
        ir = R * 0.52
        ig = QRadialGradient(cx, cy, ir)
        ib1 = QColor(C["card"]); ib1.setAlpha(240)
        ib2 = QColor(C["surface"]); ib2.setAlpha(200)
        ig.setColorAt(0, ib2); ig.setColorAt(1, ib1)
        p.setPen(Qt.NoPen); p.setBrush(ig)
        p.drawEllipse(int(cx - ir), int(cy - ir), int(ir * 2), int(ir * 2))

        # ridge lines
        pulse_val = math.sin(self._pulse)
        for i, (rr, span, offset) in enumerate([
            (ir * 0.72, 150, 20),
            (ir * 0.52, 170, 10),
            (ir * 0.33, 180,  0),
            (ir * 0.16, 360,  0),
        ]):
            rc    = QColor(c_main)
            alpha = 180 if self._state != "idle" else 70
            if self._state == "scanning":
                alpha = int(100 + 80 * pulse_val)
            rc.setAlpha(alpha)
            p.setPen(QPen(rc, 1.8 if i < 2 else 1.4)); p.setBrush(Qt.NoBrush)
            if i == 3:
                p.drawEllipse(int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2))
            else:
                p.drawArc(int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2),
                          int((200 + offset) * 16), int(span * 16))

        # center dot
        dr = ir * 0.10
        p.setPen(Qt.NoPen); p.setBrush(c_main)
        p.drawEllipse(int(cx - dr), int(cy - dr), int(dr * 2), int(dr * 2))

        # corner brackets
        blen, gap = 14, 4
        p.setPen(QPen(c_main, 2))
        for bx, by, bw, bh, dx, dy in [
            (int(cx - R - gap),        int(cy - R - gap),        blen, blen,  1,  1),
            (int(cx + R + gap - blen), int(cy - R - gap),        blen, blen, -1,  1),
            (int(cx - R - gap),        int(cy + R + gap - blen), blen, blen,  1, -1),
            (int(cx + R + gap - blen), int(cy + R + gap - blen), blen, blen, -1, -1),
        ]:
            p.drawLine(bx, by, bx + int(bw * dx * 0.5), by)
            p.drawLine(bx, by, bx, by + int(bh * dy * 0.5))

        p.end()


class StatusBar(QWidget):
    """Top status bar with clock and system info."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet(
            f"background-color: {C['surface']}; border-bottom: 1px solid {C['border']};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)

        sys_lbl = QLabel("FINGERPRINT ACCESS CONTROL SYSTEM v2")
        sys_lbl.setFont(QFont(FONT_MONO, 11, QFont.Bold))
        sys_lbl.setStyleSheet(f"color: {C['text_dim']}; letter-spacing: 2px;")
        layout.addWidget(sys_lbl)
        layout.addStretch()

        self.db_indicator = QLabel("● DATABASE")
        self.db_indicator.setFont(QFont(FONT_MONO, 11))
        self.db_indicator.setStyleSheet(f"color: {C['green']};")
        layout.addWidget(self.db_indicator)

        sep = QLabel(" | ")
        sep.setStyleSheet(f"color: {C['border_hi']};")
        layout.addWidget(sep)

        self.clock = QLabel()
        self.clock.setFont(QFont(FONT_MONO, 13, QFont.Bold))
        self.clock.setStyleSheet(f"color: {C['text']};")
        layout.addWidget(self.clock)

        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000)
        self._tick()

    def _tick(self):
        self.clock.setText(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def set_db_status(self, ok):
        self.db_indicator.setStyleSheet(
            f"color: {C['green']};" if ok else f"color: {C['red']};"
        )


class NavButton(QPushButton):
    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(60)
        self.setText(f"{icon}\n{text}")
        self.setFont(QFont(FONT_UI, 8, QFont.Bold))
        self._apply_style(False)
        self.toggled.connect(self._apply_style)

    def _apply_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C['surface']};
                    color: {C['cyan']};
                    border: none;
                    border-bottom: 3px solid {C['cyan']};
                    border-radius: 0px;
                    font-size: 12px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                    padding-top: 4px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {C['text_dim']};
                    border: none;
                    border-bottom: 3px solid transparent;
                    border-radius: 0px;
                    font-size: 12px;
                    letter-spacing: 0.5px;
                    padding-top: 4px;
                }}
                QPushButton:hover {{
                    background: {C['elevated']};
                    color: {C['text']};
                    border-bottom: 3px solid {C['border']};
                }}
            """)


class PanelCard(QFrame):
    """Styled panel card with optional title bar."""

    def __init__(self, title="", accent=None, parent=None):
        super().__init__(parent)
        self._accent = accent or C["cyan"]
        self.setObjectName("PanelCard")
        self.setStyleSheet(f"""
            QFrame#PanelCard {{
                background-color: {C['card']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                border-left: 3px solid {self._accent};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if title:
            header = QWidget()
            header.setFixedHeight(44)
            header.setStyleSheet(f"""
                QWidget {{
                    background-color: {C['elevated']};
                    border-bottom: 1px solid {C['border']};
                    border-radius: 0px;
                }}
            """)
            h_layout = QHBoxLayout(header)
            h_layout.setContentsMargins(16, 0, 16, 0)

            tag = QLabel("▐")
            tag.setStyleSheet(f"color: {self._accent}; font-size: 14px;")
            h_layout.addWidget(tag)

            lbl = QLabel(title.upper())
            lbl.setFont(QFont(FONT_MONO, 10, QFont.Bold))
            lbl.setStyleSheet(f"color: {C['text_dim']}; letter-spacing: 2px;")
            h_layout.addWidget(lbl)
            h_layout.addStretch()
            layout.addWidget(header)

        self.body        = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 14, 16, 14)
        self.body_layout.setSpacing(10)
        layout.addWidget(self.body)

    def add(self, widget):
        self.body_layout.addWidget(widget)
        return widget

    def add_layout(self, layout):
        self.body_layout.addLayout(layout)


# ── Helper factory functions ───────────────────────────────────
def big_btn(text, color="cyan", icon=""):
    btn = QPushButton(f"{icon} {text}".strip())
    btn.setMinimumHeight(58)
    btn.setFont(QFont(FONT_UI, 13, QFont.Bold))
    c       = C[color]
    c_hover = C[color + "_dim"]
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {c};
            color: #FFFFFF;
            border: none;
            border-radius: 4px;
            letter-spacing: 0.5px;
            padding: 0 24px;
        }}
        QPushButton:hover   {{ background-color: {c_hover}; color: #FFFFFF; }}
        QPushButton:pressed {{ background-color: {c};       color: #FFFFFF; }}
        QPushButton:disabled {{
            background-color: {C['border']};
            color: {C['text_muted']};
        }}
    """)
    return btn


def outline_btn(text):
    btn = QPushButton(text)
    btn.setMinimumHeight(58)
    btn.setFont(QFont(FONT_UI, 12))
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {C['surface']};
            color: {C['text_dim']};
            border: 1px solid {C['border']};
            border-radius: 4px;
            padding: 0 20px;
        }}
        QPushButton:hover {{
            background-color: {C['elevated']};
            color: {C['text']};
            border-color: {C['border_hi']};
        }}
    """)
    return btn


def field_label(text):
    lbl = QLabel(text.upper())
    lbl.setFont(QFont(FONT_MONO, 10))
    lbl.setStyleSheet(f"color: {C['text_dim']}; letter-spacing: 1.5px;")
    return lbl


def styled_input(placeholder=""):
    inp = QLineEdit()
    inp.setPlaceholderText(placeholder)
    inp.setMinimumHeight(50)
    inp.setFont(QFont(FONT_UI, 13))
    inp.setStyleSheet(f"""
        QLineEdit {{
            background-color: {C['surface']};
            border: 1px solid {C['border']};
            border-radius: 4px;
            color: {C['text']};
            padding: 0 16px;
        }}
        QLineEdit:focus {{
            border: 1.5px solid {C['cyan']};
            background-color: {C['surface']};
        }}
    """)
    return inp


def status_badge(text, color):
    lbl = QLabel(f" {text} ")
    lbl.setFont(QFont(FONT_MONO, 10, QFont.Bold))
    lbl.setStyleSheet(f"""
        color: {color};
        background-color: transparent;
        border: 1px solid {color};
        border-radius: 2px;
        padding: 3px 8px;
        letter-spacing: 1px;
    """)
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


# ══════════════════════════════════════════════════════════════
# REGISTER PAGE
# ══════════════════════════════════════════════════════════════
class RegisterPage(QWidget):
    def __init__(self):
        super().__init__()
        self._template = None
        self._worker   = None
        self.setStyleSheet(f"background: {C['bg']};")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 24)
        root.setSpacing(14)

        # ── Page header ──────────────────────────────────────
        hdr = QHBoxLayout()
        self.pg_title = QLabel("REGISTER NEW FINGERPRINT")
        self.pg_title.setFont(QFont(FONT_MONO, 17, QFont.Bold))
        self.pg_title.setStyleSheet(f"color: {C['text_hi']}; letter-spacing: 2px;")
        hdr.addWidget(self.pg_title)
        hdr.addStretch()
        self.step_badge = status_badge("STEP 1 / 2 — SCAN", C["amber"])
        hdr.addWidget(self.step_badge)
        root.addLayout(hdr)

        rule = QFrame(); rule.setFrameShape(QFrame.HLine)
        rule.setStyleSheet(f"color: {C['border']};")
        root.addWidget(rule)

        # ── 2-column layout ──────────────────────────────────
        cols = QHBoxLayout()
        cols.setSpacing(20)

        # LEFT — scanner
        left = QVBoxLayout()
        left.setSpacing(12)

        scanner_panel = PanelCard("scanner unit", C["cyan"])
        sc_body = QVBoxLayout()
        sc_body.setContentsMargins(20, 20, 20, 20)
        sc_body.setSpacing(12)
        sc_body.setAlignment(Qt.AlignCenter)

        self.ring = ScannerRing(200)
        sc_body.addWidget(self.ring, 0, Qt.AlignCenter)

        self.scan_status = QLabel("STANDBY")
        self.scan_status.setFont(QFont(FONT_MONO, 18, QFont.Bold))
        self.scan_status.setStyleSheet(f"color: {C['text_dim']}; letter-spacing: 3px;")
        self.scan_status.setAlignment(Qt.AlignCenter)
        sc_body.addWidget(self.scan_status)

        self.scan_detail = QLabel("กด CAPTURE เพื่อเริ่มการสแกน")
        self.scan_detail.setFont(QFont(FONT_UI, 12))
        self.scan_detail.setStyleSheet(f"color: {C['text_dim']};")
        self.scan_detail.setAlignment(Qt.AlignCenter)
        self.scan_detail.setWordWrap(True)
        sc_body.addWidget(self.scan_detail)

        scanner_panel.body_layout.addLayout(sc_body)
        left.addWidget(scanner_panel, 1)

        self.capture_btn = big_btn("CAPTURE FINGERPRINT", "cyan", "⬤")
        self.capture_btn.clicked.connect(self._capture)
        left.addWidget(self.capture_btn)

        cols.addLayout(left, 45)

        # RIGHT — form
        right = QVBoxLayout()
        right.setSpacing(12)

        form_panel = PanelCard("template information", C["amber"])
        form_panel.body_layout.setSpacing(12)
        form_panel.add(field_label("Template Name / Employee ID"))
        self.name_input = styled_input("เช่น EMP-0042 หรือ สมชาย ใจดี")
        form_panel.add(self.name_input)
        form_panel.add(field_label("Template Status"))
        self.tpl_info = QLabel("— รอการสแกน —")
        self.tpl_info.setFont(QFont(FONT_MONO, 10))
        self.tpl_info.setStyleSheet(f"color: {C['text_muted']}; letter-spacing: 1px;")
        form_panel.add(self.tpl_info)
        right.addWidget(form_panel)

        instr_panel = PanelCard("instructions", C["text_dim"])
        instr_panel.body_layout.setSpacing(10)
        for num, desc in [
            ("01", "วางนิ้วมือบนเครื่องอ่านให้แน่บสนิท"),
            ("02", "กดปุ่ม CAPTURE และรอสัญญาณ"),
            ("03", "กรอกชื่อ / รหัสพนักงาน"),
            ("04", "กด SAVE TO DATABASE เพื่อยืนยัน"),
        ]:
            row = QHBoxLayout()
            n   = QLabel(num)
            n.setFont(QFont(FONT_MONO, 11, QFont.Bold))
            n.setFixedWidth(32)
            n.setStyleSheet(f"color: {C['cyan']};")
            d   = QLabel(desc)
            d.setFont(QFont(FONT_UI, 12))
            d.setStyleSheet(f"color: {C['text_dim']};")
            row.addWidget(n); row.addWidget(d); row.addStretch()
            instr_panel.body_layout.addLayout(row)
        right.addWidget(instr_panel)

        right.addStretch()

        # ── Action buttons row ────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.cancel_btn = big_btn("CANCEL", "red", "✘")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._reset)
        action_row.addWidget(self.cancel_btn, 1)

        self.save_btn = big_btn("SAVE TO DATABASE", "green", "✔")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        action_row.addWidget(self.save_btn, 2)

        right.addLayout(action_row)

        cols.addLayout(right, 55)
        root.addLayout(cols)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        h = self.height(); w = self.width()
        self.ring.setFixedSize(
            max(140, min(280, int(h * 0.38))),
            max(140, min(280, int(h * 0.38)))
        )
        self.scan_status.setFont(QFont(FONT_MONO, max(13, min(24, int(h * 0.028))), QFont.Bold))
        self.scan_detail.setFont(QFont(FONT_UI,   max(10, min(15, int(h * 0.016)))))
        self.pg_title.setFont(QFont(FONT_MONO,    max(12, min(20, int(w * 0.013))), QFont.Bold))

    # ── Logic ─────────────────────────────────────────────────
    def _capture(self):
        self.capture_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.ring.set_state("scanning")
        self.scan_status.setText("SCANNING...")
        self.scan_status.setStyleSheet(f"color: {C['cyan']}; letter-spacing: 3px;")
        self.scan_detail.setText("กรุณาวางนิ้วมือ และอย่าขยับ")
        self._set_badge("SCANNING...", C["cyan"])
        self._worker = ScanWorker()
        self._worker.captured.connect(self._on_captured)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_captured(self, template):
        self._template = template
        self.ring.set_state("success")
        self.scan_status.setText("CAPTURED ✓")
        self.scan_status.setStyleSheet(f"color: {C['green']}; letter-spacing: 3px;")
        self.scan_detail.setText("สแกนสำเร็จ — กรอกข้อมูลด้านขวา แล้วกด SAVE")
        self.tpl_info.setText(
            f"SIZE: {len(template):,} chars | {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        )
        self.tpl_info.setStyleSheet(f"color: {C['green']}; letter-spacing: 1px;")
        self.capture_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)      # ← เปิดใช้งานหลังสแกนสำเร็จ
        self._set_badge("STEP 2 / 2 — SAVE", C["green"])

    def _on_failed(self, msg):
        self.ring.set_state("fail")
        self.scan_status.setText("FAILED")
        self.scan_status.setStyleSheet(f"color: {C['red']}; letter-spacing: 3px;")
        self.scan_detail.setText(msg)
        self.capture_btn.setEnabled(True)
        self._set_badge("STEP 1 / 2 — RETRY", C["red"])

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            Dialog.error(self, "ข้อผิดพลาด", "กรุณากรอกชื่อ / Template Name ก่อนบันทึก")
            return
        if not self._template:
            Dialog.error(self, "ข้อผิดพลาด", "ไม่มี Template — กรุณาสแกนก่อน")
            return
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute(
                "INSERT INTO fingerprints (user_id, template, template_size) VALUES (%s, %s, %s)",
                (name, self._template.encode(), len(self._template))
            )
            conn.commit(); cur.close(); conn.close()
            Dialog.success(self, "บันทึกสำเร็จ", f"บันทึก '{name}' เรียบร้อยแล้ว")
            self._reset()
        except Exception as e:
            Dialog.error(self, "ข้อผิดพลาด", str(e))
    
    def _flash_error(self, msg):
        Dialog.error(self, "ข้อผิดพลาด", msg)

    def _reset(self):
        self._template = None
        self.ring.set_state("idle")
        self.scan_status.setText("STANDBY")
        self.scan_status.setStyleSheet(f"color: {C['text_dim']}; letter-spacing: 3px;")
        self.scan_detail.setText("กด CAPTURE เพื่อเริ่มการสแกน")
        self.name_input.clear()
        self.tpl_info.setText("— รอการสแกน —")
        self.tpl_info.setStyleSheet(f"color: {C['text_muted']}; letter-spacing: 1px;")
        self.capture_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)     # ← ปิดใช้งานเมื่อ reset
        self._set_badge("STEP 1 / 2 — SCAN", C["amber"])

    def _set_badge(self, text, color):
        self.step_badge.setText(f" {text} ")
        self.step_badge.setStyleSheet(
            f"color:{color}; border:1px solid {color}; border-radius:2px; "
            f"padding:3px 8px; letter-spacing:1px; "
            f"font-family:{FONT_MONO}; font-size:10px; font-weight:700;"
        )


# ══════════════════════════════════════════════════════════════
# VERIFY PAGE
# ══════════════════════════════════════════════════════════════
class VerifyPage(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None
        self.setStyleSheet(f"background: {C['bg']};")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(16)

        hdr = QHBoxLayout()
        self.pg_title = QLabel("FINGERPRINT VERIFICATION")
        self.pg_title.setFont(QFont(FONT_MONO, 17, QFont.Bold))
        self.pg_title.setStyleSheet(f"color: {C['text_hi']}; letter-spacing: 2px;")
        hdr.addWidget(self.pg_title)
        hdr.addStretch()
        self.mode_badge = status_badge("STANDBY", C["text_dim"])
        hdr.addWidget(self.mode_badge)
        root.addLayout(hdr)

        rule = QFrame(); rule.setFrameShape(QFrame.HLine)
        rule.setStyleSheet(f"color: {C['border']};")
        root.addWidget(rule)

        cols = QHBoxLayout(); cols.setSpacing(20)

        # LEFT — scanner
        left = QVBoxLayout(); left.setSpacing(14)
        scan_panel = PanelCard("scanner unit", C["cyan"])
        s_body = QVBoxLayout()
        s_body.setContentsMargins(24, 24, 24, 24)
        s_body.setSpacing(14)
        s_body.setAlignment(Qt.AlignCenter)

        self.ring = ScannerRing(240)
        s_body.addWidget(self.ring, 0, Qt.AlignCenter)

        self.status_lbl = QLabel("PLACE FINGER")
        self.status_lbl.setFont(QFont(FONT_MONO, 22, QFont.Bold))
        self.status_lbl.setStyleSheet(f"color: {C['text_dim']}; letter-spacing: 4px;")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        s_body.addWidget(self.status_lbl)

        self.sub_lbl = QLabel("กด VERIFY เพื่อเริ่มการตรวจสอบตัวตน")
        self.sub_lbl.setFont(QFont(FONT_UI, 12))
        self.sub_lbl.setStyleSheet(f"color: {C['text_dim']};")
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        self.sub_lbl.setWordWrap(True)
        s_body.addWidget(self.sub_lbl)

        scan_panel.body_layout.addLayout(s_body)
        left.addWidget(scan_panel)

        self.verify_btn = big_btn("VERIFY FINGERPRINT", "cyan", "⬤")
        self.verify_btn.setMinimumHeight(58)
        self.verify_btn.clicked.connect(self._verify)
        left.addWidget(self.verify_btn)
        cols.addLayout(left, 50)

        # RIGHT — result + log
        right = QVBoxLayout(); right.setSpacing(14)

        result_panel = PanelCard("access result", C["cyan"])
        result_panel.body_layout.setSpacing(6)
        result_panel.body_layout.setContentsMargins(24, 20, 24, 20)
        result_panel.setMinimumHeight(200)

        self.result_icon = QLabel("—")
        self.result_icon.setFont(QFont(FONT_MONO, 52, QFont.Bold))
        self.result_icon.setAlignment(Qt.AlignCenter)
        self.result_icon.setStyleSheet(f"color: {C['text_muted']};")
        result_panel.add(self.result_icon)

        self.result_name = QLabel("— AWAITING SCAN —")
        self.result_name.setFont(QFont(FONT_MONO, 17, QFont.Bold))
        self.result_name.setAlignment(Qt.AlignCenter)
        self.result_name.setStyleSheet(f"color: {C['text_dim']}; letter-spacing: 2px;")
        result_panel.add(self.result_name)

        self.result_time = QLabel("")
        self.result_time.setFont(QFont(FONT_MONO, 11))
        self.result_time.setAlignment(Qt.AlignCenter)
        self.result_time.setStyleSheet(f"color: {C['text_muted']};")
        result_panel.add(self.result_time)
        right.addWidget(result_panel)

        log_panel = PanelCard("access log", C["text_dim"])
        log_panel.setMinimumHeight(160)
        self._log_rows = []
        self.log_grid  = QVBoxLayout()
        self.log_grid.setSpacing(4)
        log_panel.body_layout.addLayout(self.log_grid)
        log_panel.body_layout.addStretch()
        right.addWidget(log_panel, 1)

        cols.addLayout(right, 50)
        root.addLayout(cols)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        h = self.height(); w = self.width()
        rs = max(160, min(320, int(h * 0.42)))
        self.ring.setFixedSize(rs, rs)
        self.status_lbl.setFont(QFont(FONT_MONO, max(14, min(26, int(h * 0.030))), QFont.Bold))
        self.sub_lbl.setFont(QFont(FONT_UI,       max(10, min(15, int(h * 0.017)))))
        self.pg_title.setFont(QFont(FONT_MONO,    max(12, min(20, int(w * 0.013))), QFont.Bold))

    def _verify(self):
        self.verify_btn.setEnabled(False)
        self.ring.set_state("scanning")
        self.status_lbl.setText("SCANNING...")
        self.status_lbl.setStyleSheet(f"color: {C['cyan']}; letter-spacing: 4px;")
        self.sub_lbl.setText("วางนิ้วมือบนเครื่องอ่าน")
        self._set_mode_badge("SCANNING", C["cyan"])
        self.result_icon.setText("◌")
        self.result_icon.setStyleSheet(f"color: {C['cyan']};")
        self.result_name.setText("PROCESSING...")
        self.result_name.setStyleSheet(f"color: {C['cyan']}; letter-spacing: 2px;")
        self._worker = VerifyWorker()
        self._worker.matched.connect(self._on_match)
        self._worker.no_match.connect(self._on_no_match)
        self._worker.progress.connect(lambda m: self.sub_lbl.setText(m))
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(lambda: self.verify_btn.setEnabled(True))
        self._worker.start()

    def _on_match(self, uid):
        self.ring.set_state("success")
        self.status_lbl.setText("ACCESS GRANTED")
        self.status_lbl.setStyleSheet(f"color: {C['green']}; letter-spacing: 4px;")
        self.sub_lbl.setText("ตรวจสอบตัวตนสำเร็จ")
        self.result_icon.setText("✔")
        self.result_icon.setStyleSheet(f"color: {C['green']}; font-size: 52px;")
        self.result_name.setText(uid)
        self.result_name.setStyleSheet(f"color: {C['green']}; font-size:18px; letter-spacing:2px;")
        now = datetime.now()
        self.result_time.setText(f"เวลา {now:%H:%M:%S — %d/%m/%Y}")
        self._set_mode_badge("GRANTED", C["green"])
        self._add_log(uid, "GRANTED", C["green"])

    def _on_no_match(self):
        self.ring.set_state("fail")
        self.status_lbl.setText("ACCESS DENIED")
        self.status_lbl.setStyleSheet(f"color: {C['red']}; letter-spacing: 4px;")
        self.sub_lbl.setText("ไม่พบลายนิ้วมือในระบบ")
        self.result_icon.setText("✘")
        self.result_icon.setStyleSheet(f"color: {C['red']}; font-size: 52px;")
        self.result_name.setText("UNKNOWN USER")
        self.result_name.setStyleSheet(f"color: {C['red']}; font-size:18px; letter-spacing:2px;")
        now = datetime.now()
        self.result_time.setText(f"เวลา {now:%H:%M:%S — %d/%m/%Y}")
        self._set_mode_badge("DENIED", C["red"])
        self._add_log("UNKNOWN", "DENIED", C["red"])

    def _on_error(self, msg):
        self.ring.set_state("fail")
        self.status_lbl.setText("ERROR")
        self.status_lbl.setStyleSheet(f"color: {C['red']}; letter-spacing: 4px;")
        self.sub_lbl.setText(msg)
        self.result_icon.setText("!")
        self.result_icon.setStyleSheet(f"color: {C['amber']};")
        self.result_name.setText("SYSTEM ERROR")
        self.result_name.setStyleSheet(f"color: {C['amber']}; letter-spacing: 2px;")

    def _set_mode_badge(self, text, color):
        self.mode_badge.setText(f" {text} ")
        self.mode_badge.setStyleSheet(
            f"color:{color}; border:1px solid {color}; border-radius:2px; "
            f"padding:2px 6px; letter-spacing:1px;"
        )

    def _add_log(self, uid, status, color):
        row = QHBoxLayout(); row.setSpacing(10)
        t = QLabel(datetime.now().strftime("%H:%M:%S"))
        t.setFont(QFont(FONT_MONO, 10)); t.setFixedWidth(76)
        t.setStyleSheet(f"color: {C['text_muted']};")
        u = QLabel(uid[:24]); u.setFont(QFont(FONT_MONO, 11))
        u.setStyleSheet(f"color: {C['text']};")
        s = QLabel(status); s.setFont(QFont(FONT_MONO, 10, QFont.Bold))
        s.setAlignment(Qt.AlignRight)
        s.setStyleSheet(f"color: {color}; letter-spacing:1px;")
        row.addWidget(t); row.addWidget(u, 1); row.addWidget(s)
        wrapper = QWidget(); wrapper.setLayout(row)
        wrapper.setStyleSheet(
            f"background:{C['elevated']}; border-radius:3px; "
            f"padding:3px 6px; border-left:2px solid {color};"
        )
        self.log_grid.insertWidget(0, wrapper)
        self._log_rows.append(wrapper)
        if len(self._log_rows) > 8:
            old = self._log_rows.pop(); old.deleteLater()


# ══════════════════════════════════════════════════════════════
# RECORDS PAGE
# ══════════════════════════════════════════════════════════════
class RecordsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {C['bg']};")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(14)

        hdr = QHBoxLayout()
        self.pg_title = QLabel("DATABASE RECORDS")
        self.pg_title.setFont(QFont(FONT_MONO, 17, QFont.Bold))
        self.pg_title.setStyleSheet(f"color: {C['text_hi']}; letter-spacing: 2px;")
        hdr.addWidget(self.pg_title)
        hdr.addStretch()
        self.count_badge = status_badge("0 RECORDS", C["text_dim"])
        hdr.addWidget(self.count_badge)
        refresh = outline_btn("↺ REFRESH")
        refresh.setMinimumHeight(36); refresh.setMaximumWidth(130)
        refresh.setFont(QFont(FONT_UI, 9))
        refresh.clicked.connect(self._load)
        hdr.addWidget(refresh)
        root.addLayout(hdr)

        rule = QFrame(); rule.setFrameShape(QFrame.HLine)
        rule.setStyleSheet(f"color: {C['border']};")
        root.addWidget(rule)

        srch_row = QHBoxLayout()
        self.search = styled_input("ค้นหา ID หรือชื่อ...")
        self.search.setMaximumHeight(38)
        self.search.textChanged.connect(self._filter)
        srch_row.addWidget(self.search)
        root.addLayout(srch_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "USER ID / NAME", "TEMPLATE SIZE", "REGISTERED"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 50)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self._apply_table_style(13, 11)
        root.addWidget(self.table)

        self._all_rows = []
        self._load()

    def _apply_table_style(self, body_pt, hdr_pt):
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                font-family: {FONT_MONO};
                font-size: {body_pt}px;
                color: {C['text']};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 10px 16px;
                border-bottom: 1px solid {C['elevated']};
            }}
            QTableWidget::item:selected {{
                background-color: {C['cyan_glow']};
                color: {C['cyan']};
            }}
            QTableWidget::item:alternate {{
                background-color: {C['bg']};
            }}
            QHeaderView::section {{
                background-color: {C['elevated']};
                color: {C['text_dim']};
                font-family: {FONT_MONO};
                font-size: {hdr_pt}px;
                font-weight: 700;
                letter-spacing: 2px;
                border: none;
                border-bottom: 1px solid {C['border']};
                border-right: 1px solid {C['border']};
                padding: 10px 16px;
            }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        h = self.height(); w = self.width()
        self.pg_title.setFont(QFont(FONT_MONO, max(12, min(20, int(w * 0.013))), QFont.Bold))
        self._apply_table_style(
            max(11, min(16, int(h * 0.018))),
            max(9,  min(14, int(h * 0.015)))
        )
        row_h = max(38, min(56, int(h * 0.065)))
        for i in range(self.table.rowCount()):
            self.table.setRowHeight(i, row_h)

    def _load(self):
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute(
                "SELECT id, user_id, template_size, created_at FROM fingerprints ORDER BY id DESC"
            )
            self._all_rows = cur.fetchall()
            cur.close(); conn.close()
            self._render(self._all_rows)
        except Exception as e:
            Dialog.error(self, "Database Error", str(e))

    def _render(self, rows):
        self.table.setRowCount(len(rows))
        row_h = max(38, min(56, int(self.height() * 0.065)))
        for i, row in enumerate(rows):
            fid = row[0]; uid = row[1]; sz = row[2]
            ts  = row[3] if len(row) > 3 and row[3] else "—"
            self.table.setItem(i, 0, QTableWidgetItem(str(fid)))
            self.table.setItem(i, 1, QTableWidgetItem(str(uid)))
            self.table.setItem(i, 2, QTableWidgetItem(f"{sz:,} B"))
            self.table.setItem(i, 3, QTableWidgetItem(str(ts)[:19] if ts != "—" else "—"))
            self.table.setRowHeight(i, row_h)
        n     = len(rows)
        color = C["cyan"] if n > 0 else C["text_dim"]
        self.count_badge.setText(f" {n} RECORD{'S' if n != 1 else ''} ")
        self.count_badge.setStyleSheet(
            f"color:{color}; border:1px solid {color}; border-radius:2px; "
            f"padding:3px 8px; letter-spacing:1px; "
            f"font-family:{FONT_MONO}; font-size:10px; font-weight:700;"
        )

    def _filter(self, text):
        if not text:
            self._render(self._all_rows)
            return
        self._render([r for r in self._all_rows if text.lower() in str(r[1]).lower()])


# ══════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fingerprint Access Control System")
        self.setMinimumSize(1000, 660)
        self.resize(1200, 740)
        self.setStyleSheet(f"background: {C['bg']}; color: {C['text']};")
        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_v = QVBoxLayout(central)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)

        # Status bar
        self.status_bar = StatusBar()
        root_v.addWidget(self.status_bar)

        # Nav bar
        self.nav_bar = QFrame()
        self.nav_bar.setFixedHeight(84)
        self.nav_bar.setStyleSheet(
            f"QFrame {{ background-color: {C['surface']}; border-bottom: 1px solid {C['border']}; }}"
        )
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.tab_register = NavButton("✋", "REGISTER")
        self.tab_verify   = NavButton("◉",  "VERIFY")
        self.tab_records  = NavButton("☰",  "RECORDS")
        self.tab_register.setChecked(True)

        for tab in [self.tab_register, self.tab_verify, self.tab_records]:
            tab.setMinimumWidth(180)
            tab.setFixedHeight(80)
            tab.setFont(QFont(FONT_UI, 11, QFont.Bold))
            nav_layout.addWidget(tab)

        nav_layout.addStretch()
        ver = QLabel("FP-SYSTEM BUILD 2025")
        ver.setFont(QFont(FONT_MONO, 8))
        ver.setStyleSheet(f"color: {C['text_muted']}; padding-right: 20px; letter-spacing: 1px;")
        nav_layout.addWidget(ver)
        root_v.addWidget(self.nav_bar)

        # Page stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {C['bg']};")
        self.page_reg    = RegisterPage()
        self.page_verify = VerifyPage()
        self.page_rec    = RecordsPage()
        self.stack.addWidget(self.page_reg)
        self.stack.addWidget(self.page_verify)
        self.stack.addWidget(self.page_rec)
        root_v.addWidget(self.stack)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(36)
        footer.setStyleSheet(f"background: {C['surface']}; border-top: 1px solid {C['border']};")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 0, 24, 0)
        left_f = QLabel("● READY")
        left_f.setFont(QFont(FONT_MONO, 10))
        left_f.setStyleSheet(f"color: {C['green']};")
        f_layout.addWidget(left_f)
        f_layout.addStretch()
        right_f = QLabel("© 2025 Fingerprint ACS | Powered by INTEGRATED SUPPLIES")
        right_f.setFont(QFont(FONT_MONO, 10))
        right_f.setStyleSheet(f"color: {C['text_muted']};")
        f_layout.addWidget(right_f)
        root_v.addWidget(footer)

        # Wire nav
        self.tab_register.clicked.connect(lambda: self._nav(0))
        self.tab_verify.clicked.connect(lambda: self._nav(1))
        self.tab_records.clicked.connect(lambda: self._nav(2))

    def _nav(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, t in enumerate([self.tab_register, self.tab_verify, self.tab_records]):
            t.setChecked(i == idx)
        if idx == 2:
            self.page_rec._load()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        h = self.height()
        nav_h    = max(60, min(100, int(h * 0.11)))
        tab_font = max(9,  min(14,  int(h * 0.015)))
        self.nav_bar.setFixedHeight(nav_h)
        for tab in [self.tab_register, self.tab_verify, self.tab_records]:
            tab.setFixedHeight(nav_h - 4)
            tab.setFont(QFont(FONT_UI, tab_font, QFont.Bold))
        self.status_bar.setFixedHeight(max(40, min(60, int(h * 0.07))))


# ══════════════════════════════════════════════════════════════
# ENTRY
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor(C["bg"]))
    pal.setColor(QPalette.WindowText,      QColor(C["text"]))
    pal.setColor(QPalette.Base,            QColor(C["surface"]))
    pal.setColor(QPalette.AlternateBase,   QColor(C["elevated"]))
    pal.setColor(QPalette.Text,            QColor(C["text"]))
    pal.setColor(QPalette.Button,          QColor(C["panel"]))
    pal.setColor(QPalette.ButtonText,      QColor(C["text"]))
    pal.setColor(QPalette.Highlight,       QColor(C["cyan"]))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.Mid,             QColor(C["border"]))
    pal.setColor(QPalette.Dark,            QColor(C["border_hi"]))
    app.setPalette(pal)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())