"""桌面宠物主窗口 — PySide6 现代灵动风格"""

import os
import json
import random
import threading
import subprocess
import base64 as b64mod
import urllib.parse
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QTextEdit, QMenu, QApplication, QFrame, QMessageBox,
    QSystemTrayIcon,
)
from PySide6.QtCore import Qt, QTimer, QSize, QPoint, Signal
from PySide6.QtGui import QMovie, QImageReader, QAction, QFont, QIcon

from pet.pet_manager import discover_pets, get_current_pet_id, set_current_pet_id, PetConfig
from config_manager import load_config, save_config
from ui_theme import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
LOG_FILE = os.path.join(BASE_DIR, "pet_debug.log")


STATE_IDLE = "idle"
STATE_TALK = "talk"
STATE_THINKING = "thinking"
STATE_SLEEP_START = "sleep_start"
STATE_SLEEP_LOOP = "sleep_loop"


def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


class PetWindow(QWidget):
    # 定义信号用于线程间通信
    reply_received = Signal(str, str)  # (reply, error)
    
    def __init__(self):
        super().__init__()
        log("=== 桌面宠物启动 (PySide6) ===")
        self.config = load_config()
        self._scale = self.config["display"].get("scale", 0.4)
        self._opacity = self.config["display"].get("opacity", 1.0)
        self._bg_mode = self.config["display"].get("bg_mode", "transparent")

        flags = Qt.Window | Qt.FramelessWindowHint
        if self.config["display"].get("topmost", True):
            flags |= Qt.WindowStaysOnTopHint
        # 隐藏任务栏图标
        flags |= Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("""
            PetWindow {
                background: transparent;
                border-radius: 16px;
            }
        """)
        self.setWindowTitle("桌面宠物")
        self.setMinimumSize(60, 60)
        self.resize(200, 200)
        ix, iy = self.config["display"].get("initial_x", 200), self.config["display"].get("initial_y", 200)
        self.move(ix, iy)
        if self._opacity < 1.0:
            self.setWindowOpacity(self._opacity)

        self.state = None
        self.available_states = set()

        self.pets = discover_pets()
        log("发现宠物: " + ", ".join(f"{k}({v.name})" for k, v in self.pets.items()))
        current_id = get_current_pet_id()
        log(f"当前宠物 ID: {current_id}")
        self.pet_config = self.pets.get(current_id)
        if not self.pet_config:
            self.pet_config = PetConfig("default", {"name": "默认", "prompt": "", "gifs": {}}, BASE_DIR)

        self.movie = QMovie(self)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.finished.connect(self._on_movie_finished)

        self.label = QLabel(self)
        self.label.setMovie(self.movie)
        self.label.setAlignment(Qt.AlignCenter)

        self.chat_frame = QFrame(self)
        self.chat_frame.setObjectName("chatFrame")
        self.chat_frame.setStyleSheet(f"""
            #chatFrame {{
                background: transparent;
                border: none;
                margin: 0px;
            }}
        """)
        chat_layout = QHBoxLayout(self.chat_frame)
        chat_layout.setContentsMargins(4, 2, 4, 4)
        self.chat_entry = QTextEdit()
        # 75% opacity dark gray rounded background
        self.chat_entry.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(60, 60, 60, 191);
                color: #f0f0f0;
                border: none;
                border-radius: 10px;
                padding: 6px 10px;
                font-family: "Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI";
                font-size: 9pt;
                selection-background-color: rgba(249, 115, 22, 127);
            }}
            QTextEdit:focus {{
                background-color: rgba(70, 70, 70, 200);
            }}
            QTextEdit::placeholder {{
                color: rgba(200, 200, 200, 128);
            }}
        """)
        self.chat_entry.setPlaceholderText("输入消息... (Enter 发送)")
        self.chat_entry.setFixedHeight(34)
        self.chat_entry.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_entry.installEventFilter(self)
        chat_layout.addWidget(self.chat_entry)
        self.chat_frame.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.label, 0, Qt.AlignCenter)
        layout.addWidget(self.chat_frame)

        from ollama_client import AIClient
        llm = self.config.get("llm", {})
        self.ollama = AIClient(
            provider=llm.get("provider", "ollama"),
            base_url=llm.get("base_url", "http://localhost:11434"),
            model=llm.get("model", "qwen2.5:7b"),
            api_key=llm.get("api_key", ""),
            temperature=llm.get("temperature", 0.7),
        )
        self.ollama_msgs = [{"role": "system", "content": self.pet_config.prompt}]

        self._chat_visible = False
        self._chat_state = "input"
        self._pending_user = ""
        self._thinking_timer = None
        self._thinking_dots = 0
        self._drag_pos = None
        self._is_drag = False
        self._gif_w = 120
        self._gif_h = 120

        self._load_all_gifs()
        self._ensure_working_pet()
        if self.available_states:
            first = STATE_IDLE if STATE_IDLE in self.available_states else next(iter(self.available_states))
            self._switch_state(first)
        self.setWindowTitle(f"桌面宠物 - {self.pet_config.name}")

        self._sleep_timer = QTimer(self)
        self._sleep_timer.timeout.connect(self._check_sleep_time)
        self._sleep_timer.start(60000)
        self._check_sleep_time()
        
        # 初始化系统托盘
        self._setup_tray_icon()
        
        # 连接信号到槽
        self.reply_received.connect(self._on_reply)
        
        log("初始化完成")

    def _setup_tray_icon(self):
        """设置系统托盘图标"""
        icon_path = os.path.join(BASE_DIR, "pet.ico")
        if os.path.exists(icon_path):
            tray_icon = QIcon(icon_path)
        else:
            tray_icon = QIcon()
        
        self.tray_icon = QSystemTrayIcon(tray_icon, self)
        self.tray_icon.setToolTip(f"桌面宠物 - {self.pet_config.name}")
        
        # 创建托盘菜单
        tray_menu = QMenu()
        tray_menu.setStyleSheet(f"""
            QMenu {{ background: {BG_SURFACE}; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER}; border-radius: 8px; padding: 4px 0; }}
            QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {BG_HOVER}; color: {ACCENT}; }}
            QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
        """)
        
        show_action = QAction("显示/隐藏", self)
        show_action.triggered.connect(self._toggle_visibility)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # 双击托盘图标显示/隐藏
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
    
    def _on_tray_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visibility()
    
    def _toggle_visibility(self):
        """切换窗口显示/隐藏"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
    
    def closeEvent(self, event):
        """处理关闭事件 - 最小化到托盘而不是退出"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "桌面宠物",
            "程序已最小化到托盘，双击托盘图标可恢复",
            QSystemTrayIcon.Information,
            2000
        )
    
    # ---------------------------------------------------------------
    # GIF Loading
    # ---------------------------------------------------------------

    def _load_all_gifs(self):
        if not self.pet_config:
            return
        state_req = [
            (STATE_IDLE, "idle"), (STATE_TALK, "talk"),
            (STATE_THINKING, "thinking"),
            (STATE_SLEEP_START, "sleep_start"), (STATE_SLEEP_LOOP, "sleep_loop"),
        ]
        loaded = set()
        for state_key, cfg_key in state_req:
            path = self.pet_config.get_gif_path(cfg_key)
            if path:
                loaded.add(state_key)
        if STATE_SLEEP_START in loaded and STATE_SLEEP_LOOP in loaded:
            self.available_states.update([STATE_SLEEP_START, STATE_SLEEP_LOOP])
        for s in (STATE_IDLE, STATE_TALK, STATE_THINKING):
            if s in loaded:
                self.available_states.add(s)
        for action_name in self.pet_config.custom_actions:
            path = self.pet_config.get_gif_path(action_name)
            if path:
                self.available_states.add(action_name)

    def _get_gif_dimensions(self, path):
        try:
            reader = QImageReader(path)
            size = reader.size()
            if size.isValid():
                return size.width(), size.height()
        except Exception:
            pass
        return 120, 120

    def _get_gif_path(self, state):
        mp = {
            STATE_IDLE: "idle", STATE_TALK: "talk", STATE_THINKING: "thinking",
            STATE_SLEEP_START: "sleep_start", STATE_SLEEP_LOOP: "sleep_loop",
        }
        k = mp.get(state, state)
        return self.pet_config.get_gif_path(k)

    # ---------------------------------------------------------------
    # State / Animation
    # ---------------------------------------------------------------

    def _can_switch_to(self, s):
        return s in self.available_states

    def _switch_state(self, new_state):
        if not self._can_switch_to(new_state):
            return
        if new_state == self.state and new_state != STATE_SLEEP_START:
            return
        self.state = new_state
        path = self._get_gif_path(new_state)
        if not path:
            return
        self.movie.stop()
        self.movie.setFileName(path)
        w, h = self._get_gif_dimensions(path)
        sw = int(w * self._scale)
        sh = int(h * self._scale)
        self.movie.setScaledSize(QSize(sw, sh))
        self._gif_w = sw
        self._gif_h = sh
        self._resize_window()
        self.movie.start()

    def _on_movie_finished(self):
        if self.state == STATE_SLEEP_START:
            self._switch_state(STATE_SLEEP_LOOP)

    def _resize_window(self):
        w = max(self._gif_w, MIN_CHAT_W if self._chat_visible else 0, 60)
        h = max(self._gif_h, 60)
        if self._chat_visible and self.chat_frame.isVisible():
            h += self.chat_frame.sizeHint().height() + 4
        self.resize(max(w, 60), max(h, 60))

    # ---------------------------------------------------------------
    # Sleep
    # ---------------------------------------------------------------

    def _toggle_sleep(self):
        if self.state in (STATE_SLEEP_START, STATE_SLEEP_LOOP):
            if self._can_switch_to(STATE_IDLE):
                self._switch_state(STATE_IDLE)
        else:
            if self._can_switch_to(STATE_SLEEP_START):
                self._switch_state(STATE_SLEEP_START)

    def _check_sleep_time(self):
        h = datetime.now().hour
        in_sleep = self.state in (STATE_SLEEP_START, STATE_SLEEP_LOOP)
        if in_sleep and 8 <= h < 22 and self._can_switch_to(STATE_IDLE):
            self._switch_state(STATE_IDLE)
        elif not in_sleep and (h >= 22 or h < 8) and self._can_switch_to(STATE_SLEEP_START):
            self._switch_state(STATE_SLEEP_START)

    # ---------------------------------------------------------------
    # Mouse events (drag)
    # ---------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_drag = False
            event.accept()
        elif event.button() == Qt.RightButton:
            self._on_right_click(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_pos is not None:
            self._is_drag = True
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._is_drag:
                self._on_click(event)
            self._drag_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_chat()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def _on_click(self, event):
        self._play_random_sound()

    # ---------------------------------------------------------------
    # Sound
    # ---------------------------------------------------------------

    def _play_random_sound(self):
        if not self.pet_config:
            return
        try:
            fs = self.pet_config.get_sound_files()
            if not fs:
                return
            path = random.choice(fs)
            threading.Thread(target=self._ps_play, args=(path,), daemon=True).start()
        except Exception:
            pass

    def _ps_play(self, path):
        try:
            abs_path = os.path.abspath(path)
            file_uri = "file:///" + urllib.parse.quote(abs_path.replace("\\", "/"), safe=":/@")
            ps = (
                'Add-Type -AssemblyName PresentationCore;'
                '$u=[Uri]::new("' + file_uri + '");'
                '$p=New-Object System.Windows.Media.MediaPlayer;'
                '$p.Volume=1.0;'
                '$p.Open($u);'
                '$p.Play();'
                '$f=New-Object System.Windows.Threading.DispatcherFrame;'
                '$p.add_MediaEnded({$f.Continue=$false});'
                '$p.add_MediaFailed({param($a,$b)$f.Continue=$false});'
                '[System.Windows.Threading.Dispatcher]::PushFrame($f)'
            )
            encoded = b64mod.b64encode(ps.encode("utf-16le")).decode("ascii")
            subprocess.Popen(
                ["powershell", "-NoProfile", "-EncodedCommand", encoded],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass

    # ---------------------------------------------------------------
    # Inline Chat
    # ---------------------------------------------------------------

    def _toggle_chat(self):
        if self._chat_visible:
            self._hide_chat()
        else:
            self._show_chat()

    def _show_chat(self):
        if self._chat_visible:
            return
        self._chat_visible = True
        self.chat_frame.setVisible(True)
        self._chat_state = "input"
        self.chat_entry.clear()
        self.chat_entry.setReadOnly(False)
        self.chat_entry.setFocus()
        self._resize_window()
        if self._can_switch_to(STATE_TALK):
            self._switch_state(STATE_TALK)

    def _hide_chat(self):
        self._chat_visible = False
        self.chat_frame.setVisible(False)
        self._resize_window()
        if self.state == STATE_TALK and self._can_switch_to(STATE_IDLE):
            self._switch_state(STATE_IDLE)
            self._check_sleep_time()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
            if self._chat_visible:
                self._on_chat_enter()
                event.accept()
                return
        elif event.key() == Qt.Key_Return and (event.modifiers() & Qt.ShiftModifier):
            if self._chat_visible:
                cursor = self.chat_entry.textCursor()
                cursor.insertText("\n")
                event.accept()
                return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """Intercept Enter key on chat_entry to send messages."""
        from PySide6.QtCore import QEvent
        if obj == self.chat_entry and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                if self._chat_visible:
                    self._on_chat_enter()
                    return True
            elif event.key() == Qt.Key_Return and (event.modifiers() & Qt.ShiftModifier):
                if self._chat_visible:
                    cursor = self.chat_entry.textCursor()
                    cursor.insertText("\n")
                    return True
        return super().eventFilter(obj, event)

    def _on_chat_enter(self):
        if self._chat_state == "input":
            self._send_chat()
        elif self._chat_state == "reply":
            self._chat_state = "input"
            self.chat_entry.setReadOnly(False)
            self.chat_entry.clear()
            self.chat_entry.setFocus()
            self._auto_resize_chat()

    def _send_chat(self):
        text = self.chat_entry.toPlainText().strip()
        if not text:
            return
        self._pending_user = text
        self._chat_state = "thinking"
        self.chat_entry.setPlainText("⚡ 思考中")
        self.chat_entry.setReadOnly(True)
        if self._can_switch_to(STATE_THINKING):
            self._switch_state(STATE_THINKING)
        self._thinking_dots = 0
        self._animate_thinking_dots()
        self._save_history("user", text)
        self.ollama_msgs.append({"role": "user", "content": text})
        threading.Thread(target=self._do_ollama, daemon=True).start()

    def _animate_thinking_dots(self):
        if self._chat_state != "thinking":
            return
        self._thinking_dots = (self._thinking_dots % 3) + 1
        dots = "·" * self._thinking_dots
        self.chat_entry.setPlainText(f"⚡ 思考中{dots}")
        self._thinking_timer = QTimer.singleShot(500, self._animate_thinking_dots)

    def _do_ollama(self):
        try:
            log(f"开始 Ollama 对话，模型: {self.ollama.model}")
            log(f"消息数量: {len(self.ollama_msgs)}")
            reply = self.ollama.chat(self.ollama_msgs, timeout=120)
            log(f"Ollama 回复成功，长度: {len(reply)}")
            log(f"回复内容预览: {reply[:50]}...")
            
            # 通过信号发送到主线程
            self.reply_received.emit(reply, "")
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            log(f"Ollama 对话失败: {e}")
            log(error_trace)
            # 通过信号发送错误到主线程
            self.reply_received.emit("", str(e))

    def _on_reply(self, reply, error):
        log(f"_on_reply 被调用: reply={'有' if reply else '无'}, error={'有' if error else '无'}")
        self._chat_state = "reply"
        if self.state == STATE_THINKING and self._can_switch_to(STATE_TALK):
            log(f"切换到 talk 状态")
            self._switch_state(STATE_TALK)
        self.chat_entry.setReadOnly(False)
        self.chat_entry.clear()
        if error:
            log(f"显示错误: {error}")
            self.chat_entry.setHtml(f'<span style="color:{DANGER};">⚠ {error}</span>')
        else:
            log(f"显示回复，长度: {len(reply)}")
            self.chat_entry.setPlainText(reply)
            self.ollama_msgs.append({"role": "assistant", "content": reply})
            self._save_history("assistant", reply)
        self._auto_resize_chat()
        self.chat_entry.setReadOnly(True)
        self.chat_entry.setFocus()

    def _auto_resize_chat(self):
        doc = self.chat_entry.document()
        doc.setTextWidth(self.chat_entry.viewport().width())
        h = int(doc.size().height()) + 8
        self.chat_entry.setFixedHeight(max(32, min(h, 120)))
        self._resize_window()

    def _save_history(self, role, content):
        try:
            from chat_window import ChatHistory
            msgs = ChatHistory.load()
            msgs.append({"role": role, "content": content,
                        "time": datetime.now().strftime("%H:%M")})
            ChatHistory.save(msgs)
        except Exception:
            pass

    # ---------------------------------------------------------------
    # Right-click context menu
    # ---------------------------------------------------------------

    def _on_right_click(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {BG_SURFACE}; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER}; border-radius: 8px; padding: 4px 0; }}
            QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
            QMenu::item:selected {{ background: {BG_HOVER}; color: {ACCENT}; }}
            QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
        """)
        # Chat toggle
        if self._chat_visible:
            menu.addAction("▲ 隐藏输入框", self._hide_chat)
        else:
            menu.addAction("◉ 打开对话", self._show_chat)
        # Sleep toggle
        if STATE_SLEEP_START in self.available_states:
            lbl = "☀ 醒来" if self.state in (STATE_SLEEP_START, STATE_SLEEP_LOOP) else "🌙 入睡"
            menu.addAction(lbl, self._toggle_sleep)
        # Custom actions
        if self.pet_config.custom_actions:
            cm = menu.addMenu("✨ 个性化动作")
            for aname, acfg in self.pet_config.custom_actions.items():
                cm.addAction(f"▶ {aname}", lambda a=aname: self._trigger_custom_action(a))
        menu.addSeparator()
        # Pet switching
        if self.pets:
            pm = menu.addMenu("◆ 切换形象")
            for pid, cfg in self.pets.items():
                pm.addAction(f"{'✓' if pid == self.pet_config.id else '  '} {cfg.name}",
                            lambda p=pid: self._switch_to_pet(p))
        menu.addAction("☰ 聊天记录", self._open_history)
        menu.addSeparator()
        # Widgets
        menu.addAction("📋 待做任务", self._open_todo)
        menu.addAction("⚡ 打开 Claude", self._launch_cc_direct)
        menu.addSeparator()
        menu.addAction("⚙ 管理器...", self._open_manager)
        menu.addAction("✖ 退出", self._quit)
        menu.exec(event.globalPosition().toPoint())

    def _open_history(self):
        from chat_window import HistoryViewer
        self._history_viewer = HistoryViewer()

    def _compress_now(self):
        from chat_window import ChatHistory
        n = ChatHistory.compress(keep=100)
        if n:
            QMessageBox.information(self, "压缩完成", f"已归档 {n} 条旧记录")
        else:
            QMessageBox.information(self, "无需压缩", "记录数未达到压缩阈值")

    def _clear_chat_history(self):
        reply = QMessageBox.question(self, "确认清空",
                                     "确定要清空所有聊天记录吗？\n此操作不可撤销。")
        if reply == QMessageBox.Yes:
            from chat_window import ChatHistory
            ChatHistory.clear()
            self.ollama_msgs = [{"role": "system", "content": self.pet_config.prompt}]
            log("聊天记录已清空")
            if self._chat_visible:
                self.chat_entry.setReadOnly(False)
                self.chat_entry.clear()
                self.chat_entry.setPlainText("记录已清空")
                QTimer.singleShot(1200, self.chat_entry.clear)

    # ---------------------------------------------------------------
    # Pet switching
    # ---------------------------------------------------------------

    def _ensure_working_pet(self):
        if self.available_states:
            return
        log("当前形象无可用 GIF，尝试回退")
        for pid, cfg in self.pets.items():
            if cfg.get_gif_path("idle"):
                log(f"回退到形象: {pid}")
                set_current_pet_id(pid)
                self.pet_config = cfg
                self._load_all_gifs()
                return
        log("未找到任何可用形象")

    def _switch_to_pet(self, pet_id):
        log(f"尝试切换形象: {pet_id}")
        try:
            if pet_id == self.pet_config.id:
                return
            cfg = self.pets.get(pet_id)
            if not cfg:
                return
            if not cfg.get_gif_path("idle"):
                QMessageBox.warning(self, "切换失败", f"形象「{cfg.name}」未配置 GIF 文件。")
                return
            set_current_pet_id(pet_id)
            self.pet_config = cfg
            self.available_states.clear()
            self._load_all_gifs()
            self.ollama_msgs[0] = {"role": "system", "content": cfg.prompt}
            self.setWindowTitle(f"桌面宠物 - {cfg.name}")
            if self.available_states:
                first = STATE_IDLE if STATE_IDLE in self.available_states else next(iter(self.available_states))
                self.state = None
                self._switch_state(first)
            log("切换完成")
        except Exception as e:
            log(f"切换异常: {e}")
            import traceback; log(traceback.format_exc())

    def reload_current_pet(self, new_config=None):
        if new_config:
            self.pet_config = new_config
        old_state = self.state
        self.state = None
        self.available_states.clear()
        self._load_all_gifs()
        self.ollama_msgs[0] = {"role": "system", "content": self.pet_config.prompt}
        self.setWindowTitle(f"桌面宠物 - {self.pet_config.name}")
        if old_state in self.available_states:
            self._switch_state(old_state)
        elif STATE_IDLE in self.available_states:
            self._switch_state(STATE_IDLE)

    def reload_scale(self, new_scale: float):
        if abs(self._scale - new_scale) < 0.01:
            return
        self._scale = new_scale
        old_state = self.state
        self.state = None
        self._load_all_gifs()
        if old_state and old_state in self.available_states:
            self._switch_state(old_state)
        elif STATE_IDLE in self.available_states:
            self._switch_state(STATE_IDLE)

    def update_appearance(self, opacity=None, bg_mode=None, bg_color=None):
        if opacity is not None and abs(self._opacity - opacity) >= 0.01:
            self._opacity = opacity
            self.setWindowOpacity(opacity)
        if bg_mode is not None:
            self._bg_mode = bg_mode
        log(f"外观已更新: opacity={self._opacity:.2f} mode={self._bg_mode}")

    def _trigger_custom_action(self, action_name: str):
        if action_name not in self.pet_config.custom_actions:
            return
        cfg = self.pet_config.custom_actions[action_name]
        self._switch_state(action_name)
        if not cfg.get("loop", True):
            QTimer.singleShot(2000,
                lambda: self._switch_state(STATE_IDLE) if self.state == action_name else None)

    def _open_pet_manager(self):
        from pet_window import PetManagerDialog
        self._mgr_dlg = PetManagerDialog(self)

    def _open_manager(self):
        from manager_window import ManagerWindow
        self._mgr_win = ManagerWindow(self, self)

    def _open_todo(self):
        from widgets import TodoWidget
        self._todo_win = TodoWidget(self)

    def _launch_cc_direct(self):
        """One-click launch Claude CLI in a new terminal."""
        try:
            import subprocess
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", "claude"],
                shell=False,
            )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "启动失败", f"无法启动 Claude CLI\n{e}")


    def _open_cc(self):
        from widgets import CCMiniWidget
        self._cc_win = CCMiniWidget(self)

    # ---------------------------------------------------------------
    # Quit
    # ---------------------------------------------------------------

    def _quit(self):
        """完全退出程序"""
        self.tray_icon.hide()
        self.movie.stop()
        self.close()
        QApplication.instance().quit()

    def run(self):
        self.show()


# ==================== 宠物管理对话框 ====================

class PetManagerDialog(QWidget):
    """宠物列表管理窗口 (PySide6)"""

    def __init__(self, pet_window):
        super().__init__()
        self.pw = pet_window
        self.setWindowTitle("管理宠物形象")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(520, 500)
        self.setMinimumSize(400, 350)
        self.setStyleSheet(f"background: {BG_DEEP};")

        from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QHBoxLayout, QLineEdit, QDialog, QPushButton as QPB

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QLabel("宠物形象管理")
        hdr.setStyleSheet(f"font-size: 13pt; font-weight: bold; color: {TEXT_PRIMARY}; padding: 12px 16px 0 16px;")
        layout.addWidget(hdr)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"background: {BG_DEEP}; border: none;")
        layout.addWidget(self.scroll, 1)

        self.list_widget = QWidget()
        self.list_widget.setStyleSheet(f"background: {BG_DEEP};")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(12, 8, 12, 8)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_widget)

        foot = QWidget()
        foot.setStyleSheet(f"background: {BG_SURFACE};")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(12, 8, 12, 8)
        add_btn = QPushButton("+ 添加新形象")
        add_btn.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER))
        add_btn.clicked.connect(self._add_new_pet)
        fl.addWidget(add_btn)
        fl.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(qss_button())
        close_btn.clicked.connect(self.close)
        fl.addWidget(close_btn)
        layout.addWidget(foot)
        self._populate()
        self.show()

    def _populate(self):
        from PySide6.QtWidgets import QPushButton as QPB
        for i in range(self.list_layout.count() - 1, -1, -1):
            item = self.list_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        if not self.pw.pets:
            empty = QLabel("暂未发现宠物形象")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_TERTIARY}; padding: 40px;")
            self.list_layout.addWidget(empty)
            self.list_layout.addStretch()
            return
        for pid, cfg in self.pw.pets.items():
            is_current = pid == self.pw.pet_config.id
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {BG_ELEVATED if is_current else BG_SURFACE};
                    border: 1px solid {ACCENT if is_current else BORDER};
                    border-radius: 6px;
                    padding: 6px;
                }}
            """)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(8, 6, 8, 6)
            cl.setSpacing(10)
            icon_path = os.path.join(cfg.path, "icon.png")
            if os.path.isfile(icon_path):
                try:
                    from PySide6.QtGui import QPixmap
                    pix = QPixmap(icon_path).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon = QLabel()
                    icon.setPixmap(pix)
                    icon.setFixedSize(36, 36)
                    cl.addWidget(icon)
                except Exception:
                    pass
            info = QWidget()
            il = QVBoxLayout(info)
            il.setContentsMargins(0, 0, 0, 0)
            il.setSpacing(2)
            nt = f"{cfg.name}  ✓" if is_current else cfg.name
            nl = QLabel(nt)
            nl.setStyleSheet(f"font-weight: bold; font-size: 9pt; color: {ACCENT if is_current else TEXT_PRIMARY};")
            il.addWidget(nl)
            gc = sum(len(v) if isinstance(v, list) else 1 for v in cfg.gif_files.values())
            sl = QLabel(f"ID: {pid}  \\u00b7  {gc} 个动作")
            sl.setStyleSheet(f"color: {TEXT_TERTIARY}; font-size: 8pt;")
            il.addWidget(sl)
            cl.addWidget(info, 1)
            if not is_current:
                sb = QPushButton("切换")
                sb.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER, px=12, py=3))
                sb.clicked.connect(lambda checked, p=pid: self._switch(p))
                cl.addWidget(sb)
            self.list_layout.addWidget(card)
        self.list_layout.addStretch()

    def _switch(self, pet_id):
        self.pw._switch_to_pet(pet_id)
        self._populate()

    def _add_new_pet(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton as QPB, QMessageBox
        dlg = QDialog(self)
        dlg.setWindowTitle("添加新形象")
        dlg.setFixedSize(360, 200)
        dlg.setStyleSheet(f"background: {BG_DEEP};")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 12, 16, 0)
        t = QLabel("添加新形象")
        t.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(t)
        s = QFrame()
        s.setFrameShape(QFrame.HLine)
        s.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(s)
        layout.addSpacing(8)
        nl = QLabel("宠物名称")
        nl.setStyleSheet(f"font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(nl)
        entry = QLineEdit()
        entry.setStyleSheet(qss_input())
        entry.setPlaceholderText("输入宠物名称")
        layout.addWidget(entry)
        h = QLabel("创建后请将 GIF 文件放入对应宠物文件夹。")
        h.setStyleSheet(f"color: {TEXT_TERTIARY}; font-size: 8pt;")
        layout.addWidget(h)
        layout.addStretch()
        foot = QWidget()
        foot.setStyleSheet(f"background: {BG_SURFACE};")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(0, 8, 0, 8)

        def _do_create():
            name = entry.text().strip()
            if not name:
                return
            import re
            pet_id = re.sub(r'[^a-zA-Z0-9一-鿿_]', '', name)
            if not pet_id:
                pet_id = "new_pet"
            pet_dir = os.path.join(BASE_DIR, "pet", pet_id)
            if os.path.exists(pet_dir):
                QMessageBox.warning(dlg, "重复", f"形象「{name}」已存在")
                return
            try:
                os.makedirs(pet_dir)
                os.makedirs(os.path.join(pet_dir, "sounds"))
                tmpl = {
                    "name": name,
                    "prompt": f"你是桌面宠物{name}。用简短活泼的语气回答。",
                    "gifs": {"idle": "idle.gif", "talk": "talk.gif", "sleep_start": "sleep_0.gif", "sleep_loop": "sleep_1.gif"}
                }
                with open(os.path.join(pet_dir, "pet.json"), "w", encoding="utf-8") as f:
                    json.dump(tmpl, f, ensure_ascii=False, indent=2)
                self.pw.pets = discover_pets()
                self._populate()
                dlg.accept()
                QMessageBox.information(self, "创建成功", f"形象「{name}」已创建。\
\
请将 GIF 文件放入:\
{pet_dir}")
            except Exception as e:
                QMessageBox.critical(dlg, "创建失败", str(e))

        ok = QPushButton("确定")
        ok.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER))
        ok.clicked.connect(_do_create)
        fl.addWidget(ok)
        cancel = QPushButton("取消")
        cancel.setStyleSheet(qss_button())
        cancel.clicked.connect(dlg.reject)
        fl.addWidget(cancel)
        layout.addWidget(foot)
        entry.returnPressed.connect(_do_create)
        entry.setFocus()
        dlg.exec()
