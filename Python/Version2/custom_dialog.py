"""
custom_dialog.py
────────────────
Drop-in replacement for QMessageBox with a polished, HMI-style UI.
Matches the Fingerprint Access Control System design language.

Usage:
    from custom_dialog import Dialog

    # Success
    Dialog.success(self, "บันทึกสำเร็จ", f"บันทึก '{name}' เรียบร้อยแล้ว")

    # Error / Warning
    Dialog.error(self, "ข้อผิดพลาด", message)

    # Confirm (returns True / False)
    if Dialog.confirm(self, "ยืนยัน", "ต้องการลบข้อมูลนี้?"):
        ...
"""

import math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsOpacityEffect, QWidget
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QRect, pyqtSignal, QSize
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QLinearGradient,
    QRadialGradient, QPixmap, QPainterPath, QKeySequence
)

# ── Re-use the same palette as main app ────────────────────────
C = {
    "bg":          "#F4F6F9",
    "surface":     "#FFFFFF",
    "panel":       "#EAECF0",
    "card":        "#FFFFFF",
    "elevated":    "#F0F2F5",
    "border":      "#D8DCE3",
    "border_hi":   "#B0B8C8",
    "cyan":        "#1565C0",
    "cyan_dim":    "#5E92D2",
    "cyan_glow":   "#E3EDF8",
    "amber":       "#E65100",
    "amber_dim":   "#F09060",
    "amber_glow":  "#FFF3EC",
    "green":       "#2E7D32",
    "green_dim":   "#6AAF6E",
    "green_glow":  "#EDF7ED",
    "red":         "#C62828",
    "red_dim":     "#E07070",
    "red_glow":    "#FDECEA",
    "text":        "#1A2033",
    "text_dim":    "#5A6478",
    "text_muted":  "#9AA3B4",
    "text_hi":     "#0D1117",
}

FONT_MONO = "Consolas"
FONT_UI   = "Segoe UI"


# ══════════════════════════════════════════════════════════════
# ICON PAINTER — draws success / error / warning / confirm icons
# ══════════════════════════════════════════════════════════════
class IconWidget(QWidget):
    """Animated SVG-style icon (drawn via QPainter)."""

    KINDS = ("success", "error", "warning", "confirm")

    def __init__(self, kind="success", size=72, parent=None):
        super().__init__(parent)
        self._kind  = kind if kind in self.KINDS else "success"
        self._phase = 0.0          # 0 → 1, drives draw-on animation
        self._done  = False
        self.setFixedSize(size, size)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(14)

    def _tick(self):
        if self._phase < 1.0:
            self._phase = min(1.0, self._phase + 0.055)
            self.update()
        else:
            if not self._done:
                self._done = True
            self._anim_timer.stop()

    # ── easing ────────────────────────────────────────────────
    @staticmethod
    def _ease_out_back(t):
        c1, c3 = 1.70158, 1.70158 + 1
        return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h   = self.width(), self.height()
        cx, cy = w / 2, h / 2
        ph     = self._phase
        scale  = self._ease_out_back(ph) if ph < 1.0 else 1.0
        r      = (w * 0.44) * scale

        # ── pick colours ──────────────────────────────────────
        if   self._kind == "success":
            ring_c = QColor(C["green"]); fill_c = QColor(C["green_glow"])
        elif self._kind == "error":
            ring_c = QColor(C["red"]);   fill_c = QColor(C["red_glow"])
        elif self._kind == "warning":
            ring_c = QColor(C["amber"]); fill_c = QColor(C["amber_glow"])
        else:  # confirm
            ring_c = QColor(C["cyan"]);  fill_c = QColor(C["cyan_glow"])

        # ── filled circle ─────────────────────────────────────
        p.setPen(Qt.NoPen)
        p.setBrush(fill_c)
        p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # ── ring ─────────────────────────────────────────────
        pen = QPen(ring_c, max(2.5, r * 0.10))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # ── glyph (drawn progressively) ───────────────────────
        pen2 = QPen(ring_c, max(2.8, r * 0.13))
        pen2.setCapStyle(Qt.RoundCap)
        pen2.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen2)

        if self._kind == "success":
            # checkmark
            pts = [
                QPoint(int(cx - r * 0.40), int(cy + r * 0.00)),
                QPoint(int(cx - r * 0.07), int(cy + r * 0.38)),
                QPoint(int(cx + r * 0.40), int(cy - r * 0.32)),
            ]
            self._draw_polyline_partial(p, pts, ph)

        elif self._kind == "error":
            # ×
            offset = r * 0.33
            if ph > 0.0:
                a1 = min(1.0, ph * 2)
                a2 = max(0.0, (ph - 0.5) * 2)
                p1s = QPoint(int(cx - offset), int(cy - offset))
                p1e = QPoint(int(cx + offset), int(cy + offset))
                p2s = QPoint(int(cx + offset), int(cy - offset))
                p2e = QPoint(int(cx - offset), int(cy + offset))
                x1  = p1s.x() + (p1e.x() - p1s.x()) * a1
                y1  = p1s.y() + (p1e.y() - p1s.y()) * a1
                p.drawLine(p1s, QPoint(int(x1), int(y1)))
                x2  = p2s.x() + (p2e.x() - p2s.x()) * a2
                y2  = p2s.y() + (p2e.y() - p2s.y()) * a2
                p.drawLine(p2s, QPoint(int(x2), int(y2)))

        elif self._kind == "warning":
            # !  — vertical bar + dot
            bar_top    = int(cy - r * 0.42)
            bar_bottom = int(cy + r * 0.12)
            dot_y      = int(cy + r * 0.36)
            bar_h_now  = int((bar_bottom - bar_top) * ph)
            p.drawLine(int(cx), bar_top, int(cx), bar_top + bar_h_now)
            if ph > 0.75:
                dot_r = max(2, int(r * 0.09))
                p.setBrush(ring_c); p.setPen(Qt.NoPen)
                p.drawEllipse(int(cx - dot_r), dot_y - dot_r, dot_r * 2, dot_r * 2)

        else:  # confirm — question mark
            if ph > 0.0:
                path = QPainterPath()
                path.moveTo(cx - r * 0.20, cy - r * 0.12)
                path.cubicTo(
                    cx - r * 0.20, cy - r * 0.50,
                    cx + r * 0.40, cy - r * 0.50,
                    cx + r * 0.35, cy - r * 0.12
                )
                path.cubicTo(
                    cx + r * 0.30, cy + r * 0.12,
                    cx,            cy + r * 0.05,
                    cx,            cy + r * 0.20
                )
                p.setPen(pen2); p.setBrush(Qt.NoBrush)
                p.drawPath(path)
                dot_r = max(2, int(r * 0.09))
                p.setBrush(ring_c); p.setPen(Qt.NoPen)
                dot_y = int(cy + r * 0.40)
                p.drawEllipse(int(cx - dot_r), dot_y - dot_r, dot_r * 2, dot_r * 2)

        p.end()

    @staticmethod
    def _draw_polyline_partial(painter, pts, t):
        """Draw a polyline up to fraction t of its total length."""
        if len(pts) < 2 or t <= 0:
            return
        # compute total length
        segs = []
        total = 0.0
        for i in range(len(pts) - 1):
            dx = pts[i+1].x() - pts[i].x()
            dy = pts[i+1].y() - pts[i].y()
            l  = math.hypot(dx, dy)
            segs.append(l); total += l
        target = total * t
        drawn  = 0.0
        for i, seg_len in enumerate(segs):
            if drawn + seg_len <= target:
                painter.drawLine(pts[i], pts[i+1])
                drawn += seg_len
            else:
                remain = target - drawn
                frac   = remain / seg_len if seg_len > 0 else 0
                ex = pts[i].x() + (pts[i+1].x() - pts[i].x()) * frac
                ey = pts[i].y() + (pts[i+1].y() - pts[i].y()) * frac
                painter.drawLine(pts[i], QPoint(int(ex), int(ey)))
                break


# ══════════════════════════════════════════════════════════════
# BASE DIALOG
# ══════════════════════════════════════════════════════════════
class CustomDialog(QDialog):
    """
    Sleek, animated modal dialog matching the FP-ACS design language.

    Parameters
    ----------
    kind        : "success" | "error" | "warning" | "confirm"
    title       : string shown in the header
    message     : body text
    confirm_mode: if True, shows OK + CANCEL and exposes .accepted
    parent      : parent QWidget
    """

    def __init__(self, kind="success", title="", message="",
                 confirm_mode=False, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self._result = False

        self._kind    = kind
        self._title   = title
        self._message = message
        self._confirm = confirm_mode

        self._build()
        self._animate_in()

    # ── colour helpers ────────────────────────────────────────
    def _accent(self):
        return {
            "success": C["green"],
            "error":   C["red"],
            "warning": C["amber"],
            "confirm": C["cyan"],
        }.get(self._kind, C["cyan"])

    def _glow(self):
        return {
            "success": C["green_glow"],
            "error":   C["red_glow"],
            "warning": C["amber_glow"],
            "confirm": C["cyan_glow"],
        }.get(self._kind, C["cyan_glow"])

    # ── build UI ─────────────────────────────────────────────
    def _build(self):
        accent = self._accent()
        glow   = self._glow()

        # Outer container (gives the drop-shadow illusion via padding)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignCenter)

        # Card frame
        card = QFrame()
        card.setObjectName("DialogCard")
        card.setMinimumWidth(440)
        card.setMaximumWidth(520)
        card.setStyleSheet(f"""
            QFrame#DialogCard {{
                background-color: {C['surface']};
                border: 1px solid {C['border_hi']};
                border-top: 3px solid {accent};
                border-radius: 8px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── Header strip ──────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {C['elevated']};
                border-radius: 0px;
                border-bottom: 1px solid {C['border']};
            }}
        """)
        h_row = QHBoxLayout(header)
        h_row.setContentsMargins(20, 0, 16, 0)

        kind_tag = QLabel(f"▐  {self._kind.upper()}")
        kind_tag.setFont(QFont(FONT_MONO, 10, QFont.Bold))
        kind_tag.setStyleSheet(f"color: {accent}; letter-spacing: 3px; background: transparent;")
        h_row.addWidget(kind_tag)
        h_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {C['border']};
                border-radius: 14px;
                color: {C['text_dim']};
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {C['red_glow']};
                border-color: {C['red']};
                color: {C['red']};
            }}
        """)
        close_btn.clicked.connect(self._cancel)
        h_row.addWidget(close_btn)
        card_layout.addWidget(header)

        # ── Body ──────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(28, 28, 28, 8)
        b_layout.setSpacing(16)

        # icon + title row
        top_row = QHBoxLayout()
        top_row.setSpacing(18)
        self._icon_w = IconWidget(kind=self._kind, size=68)
        top_row.addWidget(self._icon_w, 0, Qt.AlignTop)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)
        title_lbl = QLabel(self._title)
        title_lbl.setFont(QFont(FONT_MONO, 15, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {C['text_hi']}; letter-spacing: 1px;")
        title_lbl.setWordWrap(True)
        title_col.addWidget(title_lbl)

        msg_lbl = QLabel(self._message)
        msg_lbl.setFont(QFont(FONT_UI, 12))
        msg_lbl.setStyleSheet(f"color: {C['text_dim']}; line-height: 1.5;")
        msg_lbl.setWordWrap(True)
        title_col.addWidget(msg_lbl)
        top_row.addLayout(title_col, 1)
        b_layout.addLayout(top_row)

        # thin accent rule
        rule_w = QFrame()
        rule_w.setFrameShape(QFrame.HLine)
        rule_w.setFixedHeight(1)
        rule_w.setStyleSheet(f"background: {C['border']}; border: none;")
        b_layout.addWidget(rule_w)

        card_layout.addWidget(body)

        # ── Buttons ───────────────────────────────────────────
        btn_area = QWidget()
        btn_area.setStyleSheet("background: transparent;")
        btn_row = QHBoxLayout(btn_area)
        btn_row.setContentsMargins(20, 12, 20, 20)
        btn_row.setSpacing(10)
        btn_row.addStretch()

        if self._confirm:
            cancel_btn = self._make_btn("CANCEL", ghost=True)
            cancel_btn.clicked.connect(self._cancel)
            btn_row.addWidget(cancel_btn)
            ok_btn = self._make_btn("CONFIRM", ghost=False)
            ok_btn.clicked.connect(self._ok)
            btn_row.addWidget(ok_btn)
        else:
            ok_btn = self._make_btn("OK", ghost=False)
            ok_btn.clicked.connect(self._ok)
            btn_row.addWidget(ok_btn)
            ok_btn.setFocus()

        card_layout.addWidget(btn_area)
        outer.addWidget(card)

    def _make_btn(self, text, ghost=False):
        btn = QPushButton(text)
        btn.setMinimumHeight(44)
        btn.setMinimumWidth(110)
        btn.setFont(QFont(FONT_MONO, 11, QFont.Bold))
        accent = self._accent()
        if ghost:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C['surface']};
                    color: {C['text_dim']};
                    border: 1px solid {C['border']};
                    border-radius: 4px;
                    letter-spacing: 1px;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background: {C['elevated']};
                    color: {C['text']};
                    border-color: {C['border_hi']};
                }}
                QPushButton:pressed {{
                    background: {C['panel']};
                }}
            """)
        else:
            dim = {
                "success": C["green_dim"],
                "error":   C["red_dim"],
                "warning": C["amber_dim"],
                "confirm": C["cyan_dim"],
            }.get(self._kind, C["cyan_dim"])
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 4px;
                    letter-spacing: 1px;
                    padding: 0 24px;
                }}
                QPushButton:hover   {{ background-color: {dim}; }}
                QPushButton:pressed {{ background-color: {accent}; }}
            """)
        return btn

    # ── Backdrop overlay via stylesheet (avoids QPainter conflict) ──
    def _apply_backdrop(self):
        self.setStyleSheet("background-color: rgba(20, 30, 50, 60);")

    # ── Animation ─────────────────────────────────────────────
    def _animate_in(self):
        # Apply backdrop color
        self._apply_backdrop()
        # Animate opacity on the card widget only (not self, to avoid QPainter conflict)
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self._opacity_eff.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_eff)
        self._fade = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._fade.setDuration(180)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.OutQuad)
        self._fade.start()

    def _animate_out(self, callback):
        self._fade2 = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._fade2.setDuration(120)
        self._fade2.setStartValue(1.0)
        self._fade2.setEndValue(0.0)
        self._fade2.setEasingCurve(QEasingCurve.InQuad)
        self._fade2.finished.connect(callback)
        self._fade2.start()
    # ── Actions ───────────────────────────────────────────────
    def _ok(self):
        self._result = True
        self._animate_out(self.accept)

    def _cancel(self):
        self._result = False
        self._animate_out(self.reject)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._ok()
        elif event.key() == Qt.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)

    # ── Geometry: fill parent window, card auto-centers via layout ──
    def exec_(self):
        # Find the top-level window to cover
        if self.parent():
            top = self.parent()
            while top.parent():
                top = top.parent()
            geo = top.geometry()
            self.setGeometry(geo)
        else:
            from PyQt5.QtWidgets import QApplication
            self.setGeometry(QApplication.primaryScreen().geometry())
        return super().exec_()


# ══════════════════════════════════════════════════════════════
# CONVENIENCE CLASS  (static factory methods)
# ══════════════════════════════════════════════════════════════
class Dialog:
    """
    Static helpers — use these instead of QMessageBox:

        Dialog.success(parent, "Title", "Message")
        Dialog.error(parent, "Title", "Message")
        Dialog.warning(parent, "Title", "Message")
        ok = Dialog.confirm(parent, "Title", "Message")
    """

    @staticmethod
    def success(parent, title, message):
        d = CustomDialog("success", title, message, confirm_mode=False, parent=parent)
        d.exec_()

    @staticmethod
    def error(parent, title, message):
        d = CustomDialog("error", title, message, confirm_mode=False, parent=parent)
        d.exec_()

    @staticmethod
    def warning(parent, title, message):
        d = CustomDialog("warning", title, message, confirm_mode=False, parent=parent)
        d.exec_()

    @staticmethod
    def confirm(parent, title, message) -> bool:
        d = CustomDialog("confirm", title, message, confirm_mode=True, parent=parent)
        d.exec_()
        return d._result


# ══════════════════════════════════════════════════════════════
# INTEGRATION PATCH for main app
# ══════════════════════════════════════════════════════════════
"""
In your main app, replace every QMessageBox call as follows:

BEFORE (RegisterPage._save):
    dlg = QMessageBox(self)
    dlg.setWindowTitle("บันทึกสำเร็จ")
    dlg.setIcon(QMessageBox.Information)
    dlg.setText(f"✔ บันทึก '{name}' เรียบร้อยแล้ว")
    ...
    dlg.exec_()

AFTER:
    Dialog.success(self, "บันทึกสำเร็จ", f"บันทึก '{name}' เรียบร้อยแล้ว")

──────────────────────────────────────────────────────────────

BEFORE (_flash_error):
    dlg = QMessageBox(self)
    dlg.setWindowTitle("ข้อผิดพลาด")
    dlg.setIcon(QMessageBox.Warning)
    dlg.setText(msg)
    dlg.exec_()

AFTER:
    Dialog.error(self, "ข้อผิดพลาด", msg)

──────────────────────────────────────────────────────────────

BEFORE (RecordsPage._load):
    QMessageBox.critical(self, "Database Error", str(e))

AFTER:
    Dialog.error(self, "Database Error", str(e))
"""


# ══════════════════════════════════════════════════════════════
# QUICK DEMO  (run this file directly to preview)
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = QMainWindow()
    win.setWindowTitle("Dialog Preview")
    win.resize(900, 600)
    win.setStyleSheet(f"background: {C['bg']};")

    central = QWidget()
    layout  = QVBoxLayout(central)
    layout.setAlignment(Qt.AlignCenter)
    layout.setSpacing(14)

    def mk(label, fn):
        b = QPushButton(label)
        b.setMinimumHeight(52)
        b.setMinimumWidth(260)
        b.setFont(QFont(FONT_MONO, 11, QFont.Bold))
        b.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                color: {C['text']};
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background: {C['elevated']}; border-color: {C['border_hi']}; }}
        """)
        b.clicked.connect(fn)
        layout.addWidget(b, 0, Qt.AlignCenter)

    mk("✔  SUCCESS dialog",  lambda: Dialog.success(win,  "บันทึกสำเร็จ",    "บันทึก 'EMP-0042' เรียบร้อยแล้ว"))
    mk("✘  ERROR dialog",    lambda: Dialog.error(win,    "ข้อผิดพลาด",       "ไม่สามารถเชื่อมต่อฐานข้อมูลได้\nกรุณาตรวจสอบการตั้งค่า"))
    mk("⚠  WARNING dialog",  lambda: Dialog.warning(win,  "คำเตือน",          "ไม่พบ Template — วางนิ้วใหม่อีกครั้ง"))
    result_label = QPushButton("?  CONFIRM dialog — click to test")
    result_label.setMinimumHeight(52)
    result_label.setMinimumWidth(260)
    result_label.setFont(QFont(FONT_MONO, 11, QFont.Bold))
    result_label.setStyleSheet(f"""
        QPushButton {{
            background: {C['cyan_glow']};
            border: 1px solid {C['cyan']};
            border-radius: 4px;
            color: {C['cyan']};
            letter-spacing: 1px;
        }}
        QPushButton:hover {{ background: {C['cyan']}; color: white; }}
    """)
    def do_confirm():
        ok = Dialog.confirm(win, "ยืนยันการลบ", "ต้องการลบข้อมูล 'EMP-0042' ออกจากระบบ?\nการกระทำนี้ไม่สามารถย้อนกลับได้")
        result_label.setText(f"?  ผลลัพธ์: {'CONFIRMED ✔' if ok else 'CANCELLED ✘'}")
    result_label.clicked.connect(do_confirm)
    layout.addWidget(result_label, 0, Qt.AlignCenter)

    win.setCentralWidget(central)
    win.show()
    sys.exit(app.exec_())