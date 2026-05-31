"""桌面宠物 - 主程序入口

基于 PySide6 的现代灵动桌面宠物。
集成本地 Ollama qwen2.5:7b 对话功能。
"""

import sys
import os

# HiDPI: let Qt detect scale factor automatically
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from pet_window import PetWindow
from ui_theme import APP_STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    # Set default font for all widgets
    from ui_theme import FONT
    app.setFont(FONT)

    pet = PetWindow()
    pet.run()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
