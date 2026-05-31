"""Floating widgets: Todo list, ClaudeCode calendar, ClaudeCode launcher."""

import os
import json
import subprocess
from datetime import datetime, date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen
from ui_theme import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TODO_FILE = os.path.join(BASE_DIR, "todo_list.json")
MGR_W = 580
MGR_H = 540


# ==================== Todo Widget ====================

class TodoWidget(QWidget):
    """Floating todo list, opens above pet. Size = 1/4 of manager."""

    def __init__(self, pet_window):
        super().__init__()
        self.pw = pet_window
        self._drag_pos = None
        w = 320
        h = 270

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(w, h)
        self.setMinimumSize(200, 150)

        # Position above pet
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        px = pet_window.x() + (pet_window.width() - w) // 2
        py = max(0, pet_window.y() - h - 10)
        self.move(max(0, min(px, screen.width() - w - 10)), py)

        container = QFrame()
        container.setObjectName("todoContainer")
        container.setStyleSheet(f"""
            #todoContainer {{
                background: {BG_SURFACE};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # Draggable header
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header.setFixedHeight(32)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 0, 6, 0)
        t = QLabel("待做任务")
        t.setStyleSheet(f"font-size: 10pt; font-weight: bold; color: {TEXT_PRIMARY}; background: transparent;")
        hl.addWidget(t)
        hl.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {TEXT_SECONDARY}; border: none; border-radius: 3px; font-size: 9pt; }}
            QPushButton:hover {{ background: {DANGER}33; color: {DANGER}; }}
        """)
        close_btn.clicked.connect(self.close)
        hl.addWidget(close_btn)
        header.mousePressEvent = self._press
        header.mouseMoveEvent = self._move
        cl.addWidget(header)

        # Input row
        input_row = QWidget()
        input_row.setStyleSheet("background: transparent;")
        il = QHBoxLayout(input_row)
        il.setContentsMargins(8, 4, 8, 4)
        self.todo_input = QLineEdit()
        self.todo_input.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_ELEVATED};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 8pt;
            }}
            QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
        """)
        self.todo_input.setPlaceholderText("新任务...")
        il.addWidget(self.todo_input, 1)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(26, 26)
        add_btn.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER, px=4, py=0, radius=6))
        add_btn.clicked.connect(self._add_task)
        il.addWidget(add_btn)
        self.todo_input.returnPressed.connect(self._add_task)
        cl.addWidget(input_row)

        # Task list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }}")
        self.task_list = QWidget()
        self.task_list.setStyleSheet("background: transparent;")
        self.task_layout = QVBoxLayout(self.task_list)
        self.task_layout.setContentsMargins(6, 2, 6, 2)
        self.task_layout.setSpacing(2)
        self.task_layout.addStretch()
        scroll.setWidget(self.task_list)
        cl.addWidget(scroll, 1)

        layout.addWidget(container)
        self._load_tasks()
        self.show()

    def _press(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _move(self, e):
        if e.buttons() & Qt.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def _add_task(self):
        text = self.todo_input.text().strip()
        if not text:
            return
        tasks = self._load_data()
        tasks.insert(0, {"text": text, "done": False, "created": datetime.now().strftime("%H:%M")})
        self._save_data(tasks)
        self.todo_input.clear()
        self._load_tasks()

    def _remove_task(self, index):
        tasks = self._load_data()
        if 0 <= index < len(tasks):
            tasks.pop(index)
            self._save_data(tasks)
        self._load_tasks()

    def _toggle_task(self, index):
        tasks = self._load_data()
        if 0 <= index < len(tasks):
            tasks[index]["done"] = not tasks[index]["done"]
            self._save_data(tasks)
        self._load_tasks()

    def _load_tasks(self):
        for i in range(self.task_layout.count() - 1, -1, -1):
            item = self.task_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        tasks = self._load_data()
        if not tasks:
            e = QLabel("暂无任务")
            e.setAlignment(Qt.AlignCenter)
            e.setStyleSheet(f"color: {TEXT_TERTIARY}; font-size: 8pt; background: transparent; padding: 10px;")
            self.task_layout.addWidget(e)
            self.task_layout.addStretch()
            return
        for idx, task in enumerate(reversed(tasks)):
            orig_idx = len(tasks) - 1 - idx
            row = QWidget()
            row.setStyleSheet(f"background: {BG_ELEVATED}; border-radius: 6px;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 2, 4, 2)
            rl.setSpacing(4)

            done_btn = QPushButton("✓" if task.get("done") else "○")
            done_btn.setFixedSize(20, 20)
            done_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {SUCCESS if task.get('done') else TEXT_TERTIARY};
                    border: none; font-size: 8pt; }}
                QPushButton:hover {{ color: {ACCENT}; }}
            """)
            done_btn.clicked.connect(lambda checked, i=orig_idx: self._toggle_task(i))
            rl.addWidget(done_btn)

            txt = QLabel(task["text"])
            txt.setWordWrap(True)
            txt.setStyleSheet(f"""
                font-size: 8pt; color: {TEXT_SECONDARY if task.get('done') else TEXT_PRIMARY};
                background: transparent;
                text-decoration: {'line-through' if task.get('done') else 'none'};
            """)
            rl.addWidget(txt, 1)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(18, 18)
            del_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {TEXT_TERTIARY}; border: none; font-size: 7pt; }}
                QPushButton:hover {{ color: {DANGER}; }}
            """)
            del_btn.clicked.connect(lambda checked, i=idx: self._remove_task(i))
            rl.addWidget(del_btn)

            self.task_layout.addWidget(row)
        self.task_layout.addStretch()
        # Auto-expand window based on task count
        task_count = len(tasks)
        target_h = min(500, max(270, 80 + task_count * 32))
        self.resize(self.width(), target_h)

    def _load_data(self):
        try:
            with open(TODO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_data(self, data):
        try:
            with open(TODO_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# ==================== ClaudeCode Calendar Widget ====================

class CCMiniWidget(QWidget):
    """一键启动 Claude 桌面端"""

    def __init__(self, pet_window):
        super().__init__()
        self._drag_pos = None

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(140, 60)
        self.setMinimumSize(120, 50)

        # Position beside pet
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        px = pet_window.x() + pet_window.width() + 10
        py = max(50, pet_window.y())
        self.move(min(px, screen.width() - 140 - 20), py)

        container = QFrame()
        container.setObjectName("ccContainer")
        container.setStyleSheet(f"""
            #ccContainer {{
                background: {BG_SURFACE};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header.setFixedHeight(24)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 0, 4, 0)
        logo = QLabel("⚡ Claude")
        logo.setStyleSheet(f"font-size: 8pt; font-weight: bold; color: {ACCENT}; background: transparent;")
        hl.addWidget(logo)
        hl.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {TEXT_SECONDARY}; border: none; border-radius: 2px; font-size: 8pt; }}
            QPushButton:hover {{ background: {DANGER}33; color: {DANGER}; }}
        """)
        close_btn.clicked.connect(self.close)
        hl.addWidget(close_btn)
        header.mousePressEvent = self._press
        header.mouseMoveEvent = self._move
        cl.addWidget(header)

        launch = QPushButton("⚡ 打开 Claude")
        launch.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER, px=6, py=2, radius=6))
        launch.setFixedHeight(26)
        launch.clicked.connect(self._launch_cc)
        cl.addWidget(launch, 0, Qt.AlignCenter)
        cl.addSpacing(4)

        layout.addWidget(container)
        self.show()

    def _press(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _move(self, e):
        if e.buttons() & Qt.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def _launch_cc(self):
        """Open Claude CLI in a new terminal."""
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", "claude"],
                shell=False,
            )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "启动失败", f"无法启动 Claude CLI\n{e}")

