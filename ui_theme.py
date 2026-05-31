"""Light gray theme — clean, bright design system (PySide6)."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QFontDatabase
from PySide6.QtWidgets import QPushButton, QFrame, QLabel, QHBoxLayout, QVBoxLayout

# ── Light Color Palette ──────────────────────────────────────────────
BG_DEEP = "#ececec"         # Deepest background
BG_SURFACE = "#f5f5f5"      # Surface / card
BG_ELEVATED = "#ffffff"     # Elevated cards / inputs
BG_HOVER = "#e0e0e0"       # Hover state
BG_INSET = "#dcdcdc"       # Inset / active state

ACCENT = "#f97316"          # Orange accent
ACCENT_HOVER = "#fb923c"    # Lighter accent
ACCENT_DIM = "#ea580c"      # Darker accent
ACCENT_GLOW = "#f9731622"   # Subtle glow

TEXT_PRIMARY = "#1a1a1a"    # Primary text
TEXT_SECONDARY = "#666666"  # Secondary / muted text
TEXT_TERTIARY = "#999999"   # Tertiary / placeholder text
TEXT_INVERSE = "#ffffff"    # Text on accent backgrounds

BORDER = "#d4d4d4"          # Standard border
BORDER_LIGHT = "#e0e0e0"    # Lighter border (hover)
BORDER_FOCUS = ACCENT       # Focus border

DANGER = "#ef4444"
DANGER_HOVER = "#f87171"
SUCCESS = "#22c55e"
INFO = "#3b82f6"

# ── Layout Sizing ────────────────────────────────────────────────────
PAD = 12
PAD_SM = 6
PAD_LG = 16
CHAT_BAR_H = 32
MIN_CHAT_W = 200
DISPLAY_SCALE = 0.4

# ── Fonts ─────────────────────────────────────────────────────────────
# Win11 HiDPI: Segoe UI Variable > Segoe UI > Microsoft YaHei UI (CJK fallback)
FONT = QFont("Segoe UI Variable Display", 9)
FONT_SM = QFont("Segoe UI Variable Display", 8)
FONT_BOLD = QFont("Segoe UI Variable Display", 9)
FONT_BOLD.setBold(True)
FONT_LG = QFont("Segoe UI Variable Display", 12)
FONT_LG.setBold(True)
FONT_MONO = QFont("Cascadia Code", 9)

# ── QSS Helpers ──────────────────────────────────────────────────────

def qss_button(bg=BG_ELEVATED, fg=TEXT_PRIMARY, hbg=BG_HOVER,
               pbg=BG_HOVER, radius=6, px=16, py=5):
    """Generate QSS for a modern flat button."""
    return f"""
    QPushButton {{
        background-color: {bg};
        color: {fg};
        border: none;
        border-radius: {radius}px;
        padding: {py}px {px}px;
        font-family: "Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI";
        font-size: 9pt;
    }}
    QPushButton:hover {{
        background-color: {hbg};
    }}
    QPushButton:pressed {{
        background-color: {pbg};
    }}
    """


def qss_input(bg=BG_ELEVATED, fg=TEXT_PRIMARY, border=BORDER,
              focus_border=ACCENT, radius=6):
    """Generate QSS for a modern text input."""
    return f"""
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {bg};
        color: {fg};
        border: 1px solid {border};
        border-radius: {radius}px;
        padding: 5px 8px;
        font-family: "Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI";
        font-size: 9pt;
        selection-background-color: {ACCENT}44;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {focus_border};
    }}
    """


QSS_COMBO = f"""
QComboBox {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI";
    font-size: 9pt;
}}
QComboBox:hover {{
    border: 1px solid {BORDER_LIGHT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    image: none;
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {BG_ELEVATED};
    outline: none;
}}
"""

QSS_SCROLLBAR = f"""
QScrollBar:vertical {{
    background: {BG_DEEP};
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BG_ELEVATED};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {BG_HOVER};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
"""

QSS_SLIDER = f"""
QSlider::groove:horizontal {{
    background: {BG_ELEVATED};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT_HOVER};
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
"""

QSS_TAB = f"""
QTabWidget::pane {{
    border: none;
    background: {BG_DEEP};
}}
QTabBar::tab {{
    background: {BG_SURFACE};
    color: {TEXT_SECONDARY};
    border: none;
    padding: 8px 22px;
    font-family: "Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI";
    font-size: 9pt;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    background: {BG_DEEP};
    color: {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background: {BG_HOVER};
}}
"""

QSS_CHECKBOX = f"""
QCheckBox {{
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI";
    font-size: 9pt;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {BORDER};
    background: {BG_ELEVATED};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
"""

QSS_LABEL = f"""
QLabel {{
    font-family: "Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI";
    font-size: 9pt;
    color: {TEXT_PRIMARY};
}}
"""

# ── Global app stylesheet ────────────────────────────────────────────

APP_STYLESHEET = f"""
{QSS_SCROLLBAR}
{QSS_COMBO}
{QSS_TAB}
{QSS_CHECKBOX}
{QSS_LABEL}
QToolTip {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "Segoe UI Variable Display","Segoe UI","Microsoft YaHei UI";
    font-size: 9pt;
}}
QMenu {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {BG_HOVER};
    color: {ACCENT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}
"""
