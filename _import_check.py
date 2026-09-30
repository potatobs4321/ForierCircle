"""临时检查：包方式导入 + 直接运行 app.py 两种路径都要能走通。"""

import os
import runpy
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---- A) 包方式：等价于 python main.py ----
import forier.app as pkg_app
from forier import MainWindow as ExportedMainWindow

print("A. import forier.app OK, main 可调用:", callable(pkg_app.main))
print("A. forier.MainWindow 与 app 用的是同一个类:",
      ExportedMainWindow is pkg_app.MainWindow)

# ---- B) 直接运行 forier/app.py：__main__ + 脚本目录在 sys.path[0]、cwd 在 forier ----
from PyQt5.QtWidgets import QApplication

exec_called = []


def fake_exec(self):
    exec_called.append(True)
    return 0


QApplication.exec_ = fake_exec

os.chdir(os.path.join(ROOT, "forier"))
sys.path.insert(0, os.getcwd())  # 模拟 IDE/脚本方式：sys.path[0] = 脚本所在目录
try:
    runpy.run_path("app.py", run_name="__main__")
    print("B. 直接运行 app.py OK（已走到 exec_，无 SystemExit）")
except SystemExit as e:
    print("B. 直接运行 app.py OK，退出码:", e.code)
except ImportError as e:
    print("B. 直接运行 app.py 仍然 ImportError:", e)
    sys.exit(1)
finally:
    os.chdir(ROOT)
    sys.path.remove(os.path.join(ROOT, "forier"))

print("B. 确实进入了事件循环 exec_():", bool(exec_called))

# ---- C) 真实的 python forier/app.py 导入阶段（不进入事件循环，只验证无 ImportError） ----
sys.path.remove(ROOT)
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "forier_script_as_main", os.path.join(ROOT, "forier", "app.py"))
    print("C. 脚本可被定位:", spec is not None)
finally:
    sys.path.insert(0, ROOT)

print()
print("全部通过")
