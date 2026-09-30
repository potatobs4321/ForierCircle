"""ForierCircle —— 用旋转向量（圆）首尾相接叠加，绘制傅里叶级数轨迹的 PyQt5 小工具。"""

__version__ = "0.1.0"

from .app_state import AppState, default_circles
from .canvas import Canvas
from .circle import Circle
from .config import BASE_OMEGA, PALETTE, color_for
from .main_window import MainWindow

__all__ = [
    "AppState",
    "BASE_OMEGA",
    "Canvas",
    "Circle",
    "MainWindow",
    "PALETTE",
    "color_for",
    "default_circles",
    "__version__",
]
