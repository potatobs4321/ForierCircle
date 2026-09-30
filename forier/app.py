"""程序启动：创建 QApplication 并显示主窗口。

三种运行方式都支持：

    python main.py          # 推荐：从项目根目录运行入口脚本
    python -m forier.app    # 以模块方式运行
    python forier/app.py    # 直接运行本文件（IDE 里右键 Run 也走这条）

最后一种没有父包，相对导入不可用，所以下面做了引导处理。
"""

import os
import sys

from PyQt5.QtWidgets import QApplication

if __package__ in (None, ""):
    # 被当作顶层脚本直接执行：先把项目根目录加入 sys.path，
    # 再按绝对包名导入，这样 forier/__init__.py 里的相对导入依然成立。
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from forier.main_window import MainWindow
else:
    from .main_window import MainWindow


def main(argv=None):
    """启动 GUI，返回进程退出码。argv 为空时使用 sys.argv。"""
    app = QApplication(argv if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
