"""GUI 管理窗口 — 现代灵动风格 (PySide6)"""

import os, json
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QLineEdit, QComboBox, QCheckBox, QSlider, QFrame,
    QScrollArea, QMessageBox, QFileDialog, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from pet.pet_manager import discover_pets, get_current_pet_id, PetConfig
from config_manager import (load_config, save_config, auto_detect_gifs,
                            import_pet_from_folder, delete_pet, BASE_DIR)
from ui_theme import *

DISPLAY_SCALE = 0.4


class ManagerWindow(QDialog):
    def __init__(self, parent, pet_window=None):
        super().__init__(parent)
        self.pw = pet_window
        self.config = load_config()
        self.pets = discover_pets()

        # Frameless: no Windows title bar + rounded corners
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(580, 540)
        self.setMinimumSize(500, 420)

        self._drag_pos = None

        # Outer layout: transparent window
        win_layout = QVBoxLayout(self)
        win_layout.setContentsMargins(6, 6, 6, 6)
        win_layout.setSpacing(0)

        # Main rounded container
        container = QFrame()
        container.setObjectName("mgrContainer")
        container.setStyleSheet(f"""
            #mgrContainer {{
                background: {BG_DEEP};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Custom title bar (draggable)
        bar = QWidget()
        bar.setObjectName("titleBar")
        bar.setStyleSheet(f"""
            #titleBar {{
                background: {BG_SURFACE};
                border-bottom: 1px solid {BORDER};
            }}
        """)
        bar.setFixedHeight(40)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 0, 8, 0)

        title = QLabel("桌宠管理器")
        title.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {TEXT_PRIMARY};")
        bl.addWidget(title)

        bl.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                border-radius: 4px;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background: {DANGER}33;
                color: {DANGER};
            }}
        """)
        close_btn.clicked.connect(self.close)
        bl.addWidget(close_btn)

        # Make title bar draggable
        bar.mousePressEvent = lambda e: self._titlebar_press(e)
        bar.mouseMoveEvent = lambda e: self._titlebar_move(e)

        layout.addWidget(bar)
        layout.addWidget(self._sep())

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(QSS_TAB)
        layout.addWidget(self.tabs, 1)
        self._build_import()
        self._build_actions()
        self._build_params()
        self._build_ai()
        self._build_pets()

        # Footer
        foot = QWidget()
        foot.setStyleSheet(f"background: {BG_SURFACE};")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(16, 8, 16, 8)
        fl.addStretch()
        apply_btn = QPushButton("应用所有更改")
        apply_btn.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER))
        apply_btn.clicked.connect(self._apply_all)
        fl.addWidget(apply_btn)
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(qss_button())
        close_btn.clicked.connect(self.close)
        fl.addWidget(close_btn)
        layout.addWidget(foot)
        win_layout.addWidget(container)
        self.show()

    # ── Title bar drag ─────────────────────────────────────────────
    def _titlebar_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _titlebar_move(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    def _styled_msg(self, title, text):
        """Custom styled message dialog (frameless, rounded, proper contrast)."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dlg.setAttribute(Qt.WA_TranslucentBackground)
        dlg.setFixedSize(300, 140)
        dlg.setStyleSheet("background: transparent;")

        container = QFrame()
        container.setObjectName("msgContainer")
        container.setStyleSheet(f"""
            #msgContainer {{
                background: {BG_SURFACE};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                color: {TEXT_PRIMARY};
                font-size: 10pt;
            }}
        """)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(6, 6, 6, 6)
        cl = QVBoxLayout(container)
        cl.setContentsMargins(20, 24, 20, 16)
        cl.setSpacing(16)

        t = QLabel(title)
        t.setStyleSheet(f"font-weight: bold; font-size: 11pt; color: {TEXT_PRIMARY};")
        t.setAlignment(Qt.AlignCenter)
        cl.addWidget(t)

        msg = QLabel(text)
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 9pt;")
        cl.addWidget(msg)

        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER, px=24, py=4))
        ok_btn.clicked.connect(dlg.accept)
        cl.addWidget(ok_btn, 0, Qt.AlignCenter)

        layout.addWidget(container)
        dlg.exec()

    def _sep(self):
        s = QFrame()
        s.setFrameShape(QFrame.HLine)
        s.setStyleSheet(f"color: {BORDER};")
        return s

    def _sect_title(self, parent, title, desc=""):
        w = QWidget()
        w.setStyleSheet(f"background: {BG_DEEP};")
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 16, 0, 4)
        t = QLabel(title)
        t.setStyleSheet(f"font-weight: bold; font-size: 10pt; color: {TEXT_PRIMARY};")
        wl.addWidget(t)
        if desc:
            d = QLabel(desc)
            d.setStyleSheet(f"font-size: 8pt; color: {TEXT_SECONDARY};")
            wl.addWidget(d)
        parent.addWidget(w)

    def _row(self, parent, label):
        w = QWidget()
        w.setStyleSheet(f"background: {BG_DEEP};")
        wl = QHBoxLayout(w)
        wl.setContentsMargins(2, 3, 2, 3)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 9pt;")
        lbl.setFixedWidth(100)
        wl.addWidget(lbl)
        parent.addWidget(w)
        return wl

    def _scroll_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background: {BG_DEEP}; border: none;")
        inner = QWidget()
        inner.setStyleSheet(f"background: {BG_DEEP};")
        inner.setLayout(QVBoxLayout())
        inner.layout().setContentsMargins(16, 8, 16, 8)
        inner.layout().addStretch()
        scroll.setWidget(inner)
        return scroll, inner.layout()

    # ---------------------------------------------------------------
    # Tab 1: Import
    # ---------------------------------------------------------------

    def _build_import(self):
        tab = QWidget()
        tab.setStyleSheet(f"background: {BG_DEEP};")
        scroll, layout = self._scroll_tab()
        tab.setLayout(QVBoxLayout())
        tab.layout().setContentsMargins(0, 0, 0, 0)
        tab.layout().addWidget(scroll)

        self._sect_title(layout, "从文件夹导入", "选择 GIF 素材文件夹，自动识别动作类型")
        r = self._row(layout, "素材文件夹")
        self._import_dir = ""
        self._import_entry = QLineEdit()
        self._import_entry.setStyleSheet(qss_input())
        r.addWidget(self._import_entry, 1)
        browse = QPushButton("浏览")
        browse.setStyleSheet(qss_button(px=12, py=3))
        browse.clicked.connect(self._browse_import)
        r.addWidget(browse)

        r = self._row(layout, "宠物名称")
        self._import_name = QLineEdit()
        self._import_name.setStyleSheet(qss_input())
        self._import_name.setFixedWidth(180)
        r.addWidget(self._import_name)
        h = QLabel("留空则用文件夹名")
        h.setStyleSheet(f"color: {TEXT_TERTIARY}; font-size: 8pt;")
        r.addWidget(h)
        r.addStretch()

        self._sect_title(layout, "识别结果")
        self._import_text = QTextEdit()
        self._import_text.setStyleSheet(qss_input())
        self._import_text.setFixedHeight(120)
        self._import_text.setReadOnly(True)
        layout.addWidget(self._import_text)

        btns = QWidget()
        btns.setStyleSheet(f"background: {BG_DEEP};")
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(2, 4, 2, 0)
        pre = QPushButton("预览")
        pre.setStyleSheet(qss_button(px=12, py=3))
        pre.clicked.connect(self._preview_import)
        bl.addWidget(pre)
        bl.addStretch()
        imp = QPushButton("导入素材")
        imp.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER))
        imp.clicked.connect(self._do_import)
        bl.addWidget(imp)
        layout.addWidget(btns)

        self.tabs.addTab(tab, "素材导入")

    def _browse_import(self):
        d = QFileDialog.getExistingDirectory(self, "选择 GIF 素材文件夹")
        if d:
            self._import_dir = d
            self._import_entry.setText(d)
            self._import_name.clear()
            self._preview_import()

    def _preview_import(self):
        self._import_text.clear()
        if not self._import_dir:
            self._import_text.setPlainText("请先选择文件夹")
            return
        m = auto_detect_gifs(self._import_dir)
        if not m:
            self._import_text.setPlainText("未检测到 GIF 文件")
        else:
            lines = [f"  {a:14s} ->  {f}" for a, f in m.items()]
            self._import_text.setPlainText(f"检测到 {len(m)} 个动作:\n\n" + "\n".join(lines))

    def _do_import(self):
        d = self._import_dir
        if not d:
            QMessageBox.warning(self, "提示", "请先选择文件夹")
            return
        n = self._import_name.text().strip()
        pid, r = import_pet_from_folder(d, n or None)
        if pid is None:
            QMessageBox.critical(self, "导入失败", r)
            return
        QMessageBox.information(self, "导入成功", f"宠物已导入\nID: {pid}\n动作: {len(r)} 个")
        self._refresh()

    # ---------------------------------------------------------------
    # Tab 2: Action Configuration
    # ---------------------------------------------------------------

    def _build_actions(self):
        tab = QWidget()
        tab.setStyleSheet(f"background: {BG_DEEP};")
        scroll, layout = self._scroll_tab()
        tab.setLayout(QVBoxLayout())
        tab.layout().setContentsMargins(0, 0, 0, 0)
        tab.layout().addWidget(scroll)

        self._sect_title(layout, "动作配置", "管理宠物动作与 GIF 文件的绑定关系")

        top = QWidget()
        top.setStyleSheet(f"background: {BG_DEEP};")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(2, 4, 2, 4)
        tl.addWidget(QLabel("当前宠物"))
        self._act_pet = QComboBox()
        self._act_pet.setStyleSheet(QSS_COMBO)
        self._act_pet.setFixedWidth(180)
        self._act_pet.currentTextChanged.connect(self._load_actions)
        tl.addWidget(self._act_pet)
        tl.addStretch()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(qss_button(px=12, py=3))
        refresh_btn.clicked.connect(self._load_actions)
        tl.addWidget(refresh_btn)
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER, px=12, py=3))
        save_btn.clicked.connect(self._save_actions)
        tl.addWidget(save_btn)
        layout.addWidget(top)

        # Scrollable action list
        self._act_container = QWidget()
        self._act_container.setStyleSheet(f"background: {BG_DEEP};")
        self._act_layout = QVBoxLayout(self._act_container)
        self._act_layout.setContentsMargins(2, 4, 2, 4)
        self._act_layout.setSpacing(2)
        self._act_layout.addStretch()
        layout.addWidget(self._act_container, 1)

        self._load_actions()
        self.tabs.addTab(tab, "动作配置")

    def _load_actions(self):
        # Clear
        for i in range(self._act_layout.count() - 1, -1, -1):
            item = self._act_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        self.pets = discover_pets()
        ids = list(self.pets.keys())
        self._act_pet.blockSignals(True)
        self._act_pet.clear()
        self._act_pet.addItems(ids)
        cur = get_current_pet_id()
        if cur in ids:
            self._act_pet.setCurrentText(cur)
        self._act_pet.blockSignals(False)

        pid = self._act_pet.currentText()
        cfg = self.pets.get(pid)
        if not cfg:
            lbl = QLabel("无宠物数据")
            lbl.setStyleSheet(f"color: {TEXT_TERTIARY}; padding: 20px;")
            self._act_layout.addWidget(lbl)
            self._act_layout.addStretch()
            return

        self._act_vars = {}
        self._custom_rows = {}

        # Standard actions
        for action in ["idle", "talk", "thinking", "sleep_start", "sleep_loop"]:
            self._act_row(action, cfg.get_gif_display(action), cfg)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        self._act_layout.addWidget(sep)

        self._sect_title(self._act_layout, "自定义动作", '右键菜单「个性化动作」中显示')

        for aname, acfg in cfg.custom_actions.items():
            self._custom_row(aname, acfg, cfg)

        add_btn = QPushButton("+ 添加自定义动作")
        add_btn.setStyleSheet(qss_button(px=12, py=3))
        add_btn.clicked.connect(self._add_custom_dialog)
        self._act_layout.addWidget(add_btn)

        self._act_layout.addStretch()

    def _act_row(self, action, gif_display, cfg):
        row = QWidget()
        row.setStyleSheet(f"background: {BG_DEEP};")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(4, 2, 4, 2)

        name = QLabel(action)
        name.setStyleSheet(f"font-weight: bold; color: {TEXT_PRIMARY};")
        name.setFixedWidth(100)
        rl.addWidget(name)

        gif_files = [f for f in os.listdir(cfg.path) if f.lower().endswith(".gif")]

        entry = QLineEdit()
        entry.setStyleSheet(qss_input())
        entry.setText(gif_display)
        entry.setPlaceholderText("GIF 文件名，多选用逗号分隔")
        rl.addWidget(entry, 1)

        combo = QComboBox()
        combo.setStyleSheet(QSS_COMBO)
        combo.setFixedWidth(160)
        combo.addItems([""] + gif_files)
        combo.currentTextChanged.connect(lambda t, e=entry: self._append_gif(e, t))
        rl.addWidget(combo)

        self._act_vars[action] = entry

        self._act_layout.addWidget(row)

    def _custom_row(self, aname, acfg, cfg):
        row = QWidget()
        row.setStyleSheet(f"background: {BG_DEEP};")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(4, 2, 4, 2)

        name = QLabel(aname)
        name.setStyleSheet(f"font-weight: bold; color: {ACCENT};")
        name.setFixedWidth(100)
        rl.addWidget(name)

        gv = acfg.get("gif", "")
        gd = ", ".join(gv) if isinstance(gv, list) else gv
        gif_files = [f for f in os.listdir(cfg.path) if f.lower().endswith(".gif")]

        entry = QLineEdit()
        entry.setStyleSheet(qss_input())
        entry.setText(gd)
        entry.setPlaceholderText("GIF 文件名")
        rl.addWidget(entry, 1)

        combo = QComboBox()
        combo.setStyleSheet(QSS_COMBO)
        combo.setFixedWidth(140)
        combo.addItems([""] + gif_files)
        combo.currentTextChanged.connect(lambda t, e=entry: self._append_gif(e, t))
        rl.addWidget(combo)

        loop = QCheckBox("循环")
        loop.setChecked(acfg.get("loop", True))
        loop.setStyleSheet(QSS_CHECKBOX)
        rl.addWidget(loop)

        del_btn = QPushButton("×")
        del_btn.setStyleSheet(qss_button(bg=BG_DEEP, fg=DANGER, hbg="#331111", px=10, py=2))
        del_btn.clicked.connect(lambda: self._remove_custom(aname))
        rl.addWidget(del_btn)

        self._custom_rows[aname] = (entry, loop)
        self._act_layout.addWidget(row)

    def _append_gif(self, entry, text):
        if not text:
            return
        cur = [s.strip() for s in entry.text().split(",") if s.strip()]
        if text not in cur:
            cur.append(text)
        entry.setText(", ".join(cur))

    def _add_custom_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("添加自定义动作")
        dlg.setFixedSize(340, 200)
        dlg.setStyleSheet(f"background: {BG_DEEP};")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 12, 16, 0)

        t = QLabel("添加自定义动作")
        t.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(t)
        s = QFrame()
        s.setFrameShape(QFrame.HLine)
        s.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(s)
        layout.addSpacing(8)

        nl = QLabel("动作名称")
        nl.setStyleSheet(f"font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(nl)
        entry = QLineEdit()
        entry.setStyleSheet(qss_input())
        layout.addWidget(entry)

        self._act_loop_var = QCheckBox("循环播放（关闭则播一次后回到 idle）")
        self._act_loop_var.setChecked(True)
        self._act_loop_var.setStyleSheet(QSS_CHECKBOX)
        layout.addWidget(self._act_loop_var)

        layout.addStretch()
        foot = QWidget()
        foot.setStyleSheet(f"background: {BG_SURFACE};")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(0, 8, 0, 8)

        def _ok():
            n = entry.text().strip()
            if not n:
                QMessageBox.warning(dlg, "提示", "请输入名称")
                return
            pid = self._act_pet.currentText()
            cfg = self.pets.get(pid)
            if cfg:
                cfg.custom_actions[n] = {"gif": "", "loop": self._act_loop_var.isChecked()}
                self._save_custom(pid)
                self._load_actions()
            dlg.accept()

        ok = QPushButton("确定")
        ok.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER))
        ok.clicked.connect(_ok)
        fl.addWidget(ok)

        cancel = QPushButton("取消")
        cancel.setStyleSheet(qss_button())
        cancel.clicked.connect(dlg.reject)
        fl.addWidget(cancel)

        layout.addWidget(foot)
        entry.returnPressed.connect(_ok)
        entry.setFocus()
        dlg.exec()

    def _remove_custom(self, aname):
        pid = self._act_pet.currentText()
        cfg = self.pets.get(pid)
        if cfg and aname in cfg.custom_actions:
            del cfg.custom_actions[aname]
            self._save_custom(pid)
        self._load_actions()

    def _save_custom(self, pid):
        cfg = self.pets.get(pid)
        if not cfg:
            return
        try:
            with open(os.path.join(cfg.path, "pet.json"), "r", encoding="utf-8") as f:
                d = json.load(f)
            d["custom_actions"] = dict(cfg.custom_actions)
            with open(os.path.join(cfg.path, "pet.json"), "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _save_actions(self):
        pid = self._act_pet.currentText()
        if not pid or pid not in self.pets:
            QMessageBox.warning(self, "提示", "请先选择宠物")
            return
        self._collect_and_save(pid)
        self.pets = discover_pets()
        if self.pw and pid == self.pw.pet_config.id:
            self.pw.reload_current_pet(self.pets[pid])
        QMessageBox.information(self, "已保存", "动作配置已写入 pet.json")

    def _collect_and_save(self, pid):
        cfg = self.pets.get(pid)
        if not cfg:
            return
        ng = {}
        for action, entry in self._act_vars.items():
            v = entry.text().strip()
            if v:
                fs = [f.strip() for f in v.split(",") if f.strip()]
                ng[action] = fs if len(fs) > 1 else fs[0]
        cd = {}
        for aname, (entry, loop) in self._custom_rows.items():
            v = entry.text().strip()
            fs = [f.strip() for f in v.split(",") if f.strip()] if v else []
            cd[aname] = {"gif": fs if len(fs) > 1 else (fs[0] if fs else ""), "loop": loop.isChecked()}
        try:
            with open(os.path.join(cfg.path, "pet.json"), "r", encoding="utf-8") as f:
                d = json.load(f)
            d["gifs"] = ng
            d["custom_actions"] = cd
            with open(os.path.join(cfg.path, "pet.json"), "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------------------------------------------------------------
    # Tab 3: Parameters
    # ---------------------------------------------------------------

    def _build_params(self):
        tab = QWidget()
        tab.setStyleSheet(f"background: {BG_DEEP};")
        scroll, layout = self._scroll_tab()
        tab.setLayout(QVBoxLayout())
        tab.layout().setContentsMargins(0, 0, 0, 0)
        tab.layout().addWidget(scroll)

        disp = self.config.get("display", {})
        self._sect_title(layout, "基础参数")

        r = self._row(layout, "缩放比例")
        self._scale_slider = QSlider(Qt.Horizontal)
        self._scale_slider.setRange(10, 100)
        self._scale_slider.setValue(int(disp.get("scale", 0.4) * 100))
        self._scale_slider.setStyleSheet(QSS_SLIDER)
        r.addWidget(self._scale_slider)
        self._scale_label = QLabel(f"{self._scale_slider.value()}%")
        self._scale_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 8pt;")
        self._scale_label.setFixedWidth(40)
        r.addWidget(self._scale_label)
        self._scale_slider.valueChanged.connect(lambda v: self._scale_label.setText(f"{v}%"))

        r = self._row(layout, "不透明度")
        self._alpha_slider = QSlider(Qt.Horizontal)
        self._alpha_slider.setRange(20, 100)
        self._alpha_slider.setValue(int(disp.get("opacity", 1.0) * 100))
        self._alpha_slider.setStyleSheet(QSS_SLIDER)
        r.addWidget(self._alpha_slider)
        self._alpha_label = QLabel(f"{self._alpha_slider.value()}%")
        self._alpha_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 8pt;")
        self._alpha_label.setFixedWidth(40)
        r.addWidget(self._alpha_label)
        self._alpha_slider.valueChanged.connect(lambda v: self._alpha_label.setText(f"{v}%"))

        r = self._row(layout, "初始位置")
        self._posx = QLineEdit(str(disp.get("initial_x", 200)))
        self._posx.setStyleSheet(qss_input())
        self._posx.setFixedWidth(70)
        r.addWidget(self._posx)
        r.addWidget(QLabel(" Y "))
        self._posy = QLineEdit(str(disp.get("initial_y", 200)))
        self._posy.setStyleSheet(qss_input())
        self._posy.setFixedWidth(70)
        r.addWidget(self._posy)
        r.addStretch()

        self._top = QCheckBox("窗口置顶")
        self._top.setChecked(disp.get("topmost", True))
        self._top.setStyleSheet(QSS_CHECKBOX)
        layout.addWidget(self._top)
        layout.addStretch()
        self.tabs.addTab(tab, "参数设置")

    # ---------------------------------------------------------------
    # Tab 3: AI Settings
    # ---------------------------------------------------------------

    def _build_ai(self):
        tab = QWidget()
        tab.setStyleSheet(f"background: {BG_DEEP};")
        scroll, layout = self._scroll_tab()
        tab.setLayout(QVBoxLayout())
        tab.layout().setContentsMargins(0, 0, 0, 0)
        tab.layout().addWidget(scroll)

        llm = self.config.get("llm", {})
        self._sect_title(layout, "模型配置")

        r = self._row(layout, "服务商")
        self._ai_prov = QComboBox()
        self._ai_prov.setStyleSheet(QSS_COMBO)
        self._ai_prov.addItems(["ollama", "openai", "deepseek", "siliconflow", "openrouter", "custom"])
        self._ai_prov.setCurrentText(llm.get("provider", "ollama"))
        self._ai_prov.currentTextChanged.connect(self._on_ai_prov)
        r.addWidget(self._ai_prov)
        r.addStretch()

        r = self._row(layout, "Base URL")
        self._ai_url = QLineEdit(llm.get("base_url", "http://localhost:11434"))
        self._ai_url.setStyleSheet(qss_input())
        r.addWidget(self._ai_url, 1)

        r = self._row(layout, "Model")
        self._ai_model = QLineEdit(llm.get("model", "qwen2.5:7b"))
        self._ai_model.setStyleSheet(qss_input())
        r.addWidget(self._ai_model, 1)

        r = self._row(layout, "API Key")
        self._ai_key = QLineEdit(llm.get("api_key", ""))
        self._ai_key.setStyleSheet(qss_input())
        self._ai_key.setEchoMode(QLineEdit.Password)
        r.addWidget(self._ai_key, 1)

        layout.addStretch()
        self.tabs.addTab(tab, "AI 设置")

    def _on_ai_prov(self, prov):
        presets = {
            "ollama": ("http://localhost:11434", "qwen2.5:7b"),
            "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
            "siliconflow": ("https://api.siliconflow.cn/v1", "Qwen/Qwen2.5-7B-Instruct"),
            "openrouter": ("https://openrouter.ai/api/v1", "openai/gpt-4o-mini"),
        }
        if prov in presets:
            u, m = presets[prov]
            self._ai_url.setText(u)
            self._ai_model.setText(m)

    # ---------------------------------------------------------------
    # Tab 4: Pet Management
    # ---------------------------------------------------------------

    def _build_pets(self):
        tab = QWidget()
        tab.setStyleSheet(f"background: {BG_DEEP};")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        top = QWidget()
        top.setStyleSheet(f"background: {BG_DEEP};")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(16, 8, 16, 4)
        lbl = QLabel("已安装宠物")
        lbl.setStyleSheet(f"font-weight: bold; color: {TEXT_PRIMARY};")
        tl.addWidget(lbl)
        tl.addStretch()
        ref = QPushButton("刷新")
        ref.setStyleSheet(qss_button(px=12, py=3))
        ref.clicked.connect(self._load_pet_list)
        tl.addWidget(ref)
        layout.addWidget(top)

        self._pet_scroll = QScrollArea()
        self._pet_scroll.setWidgetResizable(True)
        self._pet_scroll.setFrameShape(QFrame.NoFrame)
        self._pet_scroll.setStyleSheet(f"background: {BG_DEEP}; border: none;")
        self._pet_list = QWidget()
        self._pet_list.setStyleSheet(f"background: {BG_DEEP};")
        self._pet_ll = QVBoxLayout(self._pet_list)
        self._pet_ll.setContentsMargins(12, 4, 12, 4)
        self._pet_ll.setSpacing(4)
        self._pet_ll.addStretch()
        self._pet_scroll.setWidget(self._pet_list)
        layout.addWidget(self._pet_scroll, 1)

        self._load_pet_list()
        self.tabs.addTab(tab, "宠物管理")

    def _load_pet_list(self):
        for i in range(self._pet_ll.count() - 1, -1, -1):
            item = self._pet_ll.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self.pets = discover_pets()
        cur = get_current_pet_id()
        if not self.pets:
            e = QLabel("暂无宠物")
            e.setAlignment(Qt.AlignCenter)
            e.setStyleSheet(f"color: {TEXT_TERTIARY}; padding: 40px;")
            self._pet_ll.addWidget(e)
            self._pet_ll.addStretch()
            return

        for pid, cfg in self.pets.items():
            active = pid == cur
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {BG_ELEVATED if active else BG_SURFACE};
                    border: 1px solid {ACCENT if active else BORDER};
                    border-radius: 6px;
                    padding: 6px;
                }}
            """)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(8, 6, 8, 6)
            cl.setSpacing(10)

            ip = os.path.join(cfg.path, "icon.png")
            if os.path.isfile(ip):
                try:
                    pix = QPixmap(ip).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    ic = QLabel()
                    ic.setPixmap(pix)
                    ic.setFixedSize(34, 34)
                    cl.addWidget(ic)
                except Exception:
                    pass

            info = QWidget()
            il = QVBoxLayout(info)
            il.setContentsMargins(0, 0, 0, 0)
            il.setSpacing(2)
            nt = f"{cfg.name}  ✓ 当前" if active else cfg.name
            nl = QLabel(nt)
            nl.setStyleSheet(f"font-weight: bold; color: {ACCENT if active else TEXT_PRIMARY};")
            il.addWidget(nl)
            gifs = len([f for f in os.listdir(cfg.path) if f.lower().endswith(".gif")])
            sl = QLabel(f"{len(cfg.gif_files)} 个动作 · {gifs} GIF")
            sl.setStyleSheet(f"color: {TEXT_TERTIARY}; font-size: 8pt;")
            il.addWidget(sl)
            cl.addWidget(info, 1)

            btns = QWidget()
            btl = QHBoxLayout(btns)
            btl.setContentsMargins(0, 0, 0, 0)
            btl.setSpacing(4)
            if not active:
                sw = QPushButton("切换")
                sw.setStyleSheet(qss_button(bg=ACCENT, fg="#fff", hbg=ACCENT_HOVER, px=10, py=3))
                sw.clicked.connect(lambda checked, p=pid: self._switch_pet(p))
                btl.addWidget(sw)
            dl = QPushButton("删除")
            dl.setStyleSheet(qss_button(bg=BG_DEEP, fg=DANGER, hbg="#331111", px=10, py=3))
            dl.clicked.connect(lambda checked, p=pid: self._delete_pet(p))
            btl.addWidget(dl)
            cl.addWidget(btns)
            self._pet_ll.addWidget(card)
        self._pet_ll.addStretch()

    def _switch_pet(self, pid):
        self.config["current_pet"] = pid
        save_config(self.config)
        self._load_pet_list()
        if self.pw:
            self.pw._switch_to_pet(pid)

    def _delete_pet(self, pid):
        cur = get_current_pet_id()
        if pid == cur:
            QMessageBox.warning(self, "无法删除", "请先切换到其他宠物")
            return
        r = QMessageBox.question(self, "确认删除", "确定删除此宠物？不可撤销。")
        if r != QMessageBox.Yes:
            return
        if delete_pet(pid):
            self._refresh()
            self._load_pet_list()
        else:
            QMessageBox.critical(self, "删除失败", "")

    # ---------------------------------------------------------------
    # Apply
    # ---------------------------------------------------------------

    def _apply_all(self):
        self.config["display"]["scale"] = self._scale_slider.value() / 100
        self.config["display"]["topmost"] = self._top.isChecked()
        self.config["display"]["opacity"] = self._alpha_slider.value() / 100
        try:
            self.config["display"]["initial_x"] = int(self._posx.text())
            self.config["display"]["initial_y"] = int(self._posy.text())
        except ValueError:
            pass
        self.config["llm"] = {
            "provider": self._ai_prov.currentText(),
            "base_url": self._ai_url.text(),
            "model": self._ai_model.text(),
            "api_key": self._ai_key.text(),
            "temperature": 0.7,
        }
        save_config(self.config)
        if self.pw:
            self._notify_pw()
        self._styled_msg("已应用", "所有配置已保存")

    def _notify_pw(self):
        pw = self.pw
        if not pw:
            return
        llm = self.config.get("llm", {})
        from ollama_client import AIClient
        pw.ollama = AIClient(
            provider=llm.get("provider", "ollama"),
            base_url=llm.get("base_url", "http://localhost:11434"),
            model=llm.get("model", "qwen2.5:7b"),
            api_key=llm.get("api_key", ""),
            temperature=llm.get("temperature", 0.7),
        )
        pw.update_appearance(opacity=self.config["display"].get("opacity", 1.0),
                             bg_mode=self.config["display"].get("bg_mode", "transparent"))
        ns = self.config["display"].get("scale", 0.4)
        if abs(pw._scale - ns) >= 0.01:
            pw.reload_scale(ns)
        pw.pets = discover_pets()
        # Refresh current pet config without switching pet
        cur_id = pw.pet_config.id
        if cur_id in pw.pets:
            pw.reload_current_pet(pw.pets[cur_id])

    def _refresh(self):
        self.pets = discover_pets()
        self._load_pet_list()


def open_manager(parent, pet_window=None):
    return ManagerWindow(parent, pet_window)
