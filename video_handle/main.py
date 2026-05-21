"""视频转图片工具入口。

运行:
    python main.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui_main import MainWindow


def main() -> int:
    """创建 Qt 应用并显示主窗口。"""
    app = QApplication(sys.argv)
    app.setApplicationName("Video Frame Exporter")
    app.setOrganizationName("CommercialTools")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
