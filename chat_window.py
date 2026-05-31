"""聊天记录管理 + 气泡风格历史查看器 (PySide6) — 圆角无边框"""

import os
import json
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from ui_theme import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")
ARCHIVE_FILE = os.path.join(BASE_DIR, "chat_archive.txt")


# ==================== 历史记录管理 ====================
class ChatHistory:
    @staticmethod
    def load():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    @staticmethod
    def save(msgs):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(msgs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def clear():
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def compress(keep=100):
        msgs = ChatHistory.load()
        if len(msgs) <= keep:
            return 0
        old = msgs[:-keep]
        try:
            with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n===== 归档于 {datetime.now().strftime('%Y-%m-%d %H:%M')} =====\n")
                for m in old:
                    f.write(f"[{m.get('time','')}] {m.get('role','')}: {m.get('content','')}\n")
                f.write("=" * 50 + "\n")
            ChatHistory.save(msgs[-keep:])
        except Exception:
            return 0
        return len(old)


# ==================== 气泡历史查看器 ====================
class HistoryViewer(QWidget):
    """Borderless, rounded-corner chat bubble history viewer."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("聊天记录")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(500, 440)
        self.setMinimumSize(320, 280)

        self._drag_pos = None
        self.setStyleSheet(f"""
            HistoryViewer {{
                background: transparent;
            }}
        """)

        # Main rounded container
        container = QFrame()
        container.setObjectName("histContainer")
        container.setStyleSheet(f"""
            #histContainer {{
                background: {BG_SURFACE};
                border-radius: 12px;
                border: 1px solid {BORDER};
            }}
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)

        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # Draggable header
        header = QWidget()
        header.setObjectName("histHeader")
        header.setStyleSheet(f"""
            #histHeader {{
                background: transparent;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
        """)
        header.setFixedHeight(40)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 8, 0)
        title = QLabel("聊天记录")
        title.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent;")
        hl.addWidget(title)
        hl.addStretch()
        self._info = QLabel()
        self._info.setStyleSheet(f"font-size: 8pt; color: {TEXT_TERTIARY}; background: transparent;")
        hl.addWidget(self._info)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {TEXT_SECONDARY}; border: none; border-radius: 4px; font-size: 10pt; }}
            QPushButton:hover {{ background: {DANGER}33; color: {DANGER}; }}
        """)
        close_btn.clicked.connect(self.close)
        hl.addWidget(close_btn)

        header.mousePressEvent = self._titlebar_press
        header.mouseMoveEvent = self._titlebar_move
        cl.addWidget(header)

        # Scroll area (no border)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: transparent; width: 4px; }}
            QScrollBar::handle:vertical {{ background: {BORDER_LIGHT}; border-radius: 2px; min-height: 20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self.bubble_container = QWidget()
        self.bubble_container.setStyleSheet("background: transparent;")
        self.bubble_layout = QVBoxLayout(self.bubble_container)
        self.bubble_layout.setContentsMargins(12, 4, 12, 4)
        self.bubble_layout.setSpacing(6)
        self.bubble_layout.addStretch()
        self.scroll.setWidget(self.bubble_container)
        cl.addWidget(self.scroll, 1)

        # Footer buttons
        foot = QWidget()
        foot.setStyleSheet("background: transparent;")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(10, 6, 10, 10)
        for txt, cb, ac in [
            ("刷新", self._refresh, False),
            ("压缩", self._compress, False),
            ("清空", self._clear_all, True),
        ]:
            btn = QPushButton(txt)
            if ac:
                btn.setStyleSheet(qss_button(bg=BG_SURFACE, fg=DANGER, hbg="#fdd", px=10, py=3))
            else:
                btn.setStyleSheet(qss_button(px=10, py=3))
            btn.clicked.connect(cb)
            fl.addWidget(btn)
        fl.addStretch()
        close2 = QPushButton("关闭")
        close2.setStyleSheet(qss_button(px=10, py=3))
        close2.clicked.connect(self.close)
        fl.addWidget(close2)
        cl.addWidget(foot)

        main_layout.addWidget(container)
        self._refresh()
        self.show()

    def _titlebar_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _titlebar_move(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _refresh(self):
        msgs = ChatHistory.load()
        self._info.setText(f"共 {len(msgs)} 条")
        for i in range(self.bubble_layout.count() - 1, -1, -1):
            item = self.bubble_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        if not msgs:
            empty = QLabel("暂无聊天记录")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_TERTIARY}; padding: 40px; background: transparent;")
            self.bubble_layout.addWidget(empty)
            self.bubble_layout.addStretch()
            return
        for m in msgs:
            self._add_bubble(m.get("role", "?"), m.get("content", ""), m.get("time", ""))
        self.bubble_layout.addStretch()
        QTimer.singleShot(100, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    def _add_bubble(self, role, content, timestamp):
        is_user = role == "user"
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        if is_user:
            rl.addStretch(1)
        bubble_bg = ACCENT if is_user else BG_ELEVATED
        bubble_fg = "#fff" if is_user else TEXT_PRIMARY
        bubble = QFrame()
        bubble.setStyleSheet(f"""
            QFrame {{ background: {bubble_bg}; border-radius: 10px; padding: 8px 12px; }}
            QLabel {{ background: transparent; color: {bubble_fg}; font-size: 9pt; }}
        """)
        bl = QVBoxLayout(bubble)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(2)
        ts = QLabel(timestamp)
        ts.setStyleSheet(f"color: {TEXT_TERTIARY if is_user else TEXT_SECONDARY}; font-size: 7pt; background: transparent;")
        ts.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)
        bl.addWidget(ts)
        lbl = QLabel(content)
        lbl.setWordWrap(True)
        lbl.setMaximumWidth(360)
        bl.addWidget(lbl)
        rl.addWidget(bubble)
        if not is_user:
            rl.addStretch(1)
        self.bubble_layout.addWidget(row)

    def _clear_all(self):
        r = QMessageBox.question(self, "确认清空", "确定要清空所有聊天记录吗？\n此操作不可撤销。")
        if r == QMessageBox.Yes:
            ChatHistory.clear()
            self._refresh()

    def _compress(self):
        n = ChatHistory.compress(keep=100)
        if n:
            QMessageBox.information(self, "压缩完成", f"已归档 {n} 条旧记录")
        else:
            QMessageBox.information(self, "无需压缩", "记录数未达阈值")
        self._refresh()
