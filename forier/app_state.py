"""画布与主窗口之间共享的应用状态。

替代原先在 MainWindow 里手写的 dict（'circles' / 'selected' /
'on_selection_changed'），语义保持不变，只是改成显式对象。
"""

from .circle import Circle

# 初始向量：(半径, 角速度)
# 半径单位 = 画布像素；三者相加 585 就是末端点离原点的最远距离，
# 所以默认窗口不能太小，否则轨迹会跑出画布（见 MainWindow.resize）
DEFAULT_CIRCLES = ((360.0, 1), (150.0, 3), (75.0, -5))


def default_circles():
    """构造默认的初始向量列表。"""
    return [Circle(radius, speed) for radius, speed in DEFAULT_CIRCLES]


class AppState:
    """共享状态：向量列表、当前选中下标、选中变化回调。

    on_selection_changed: 无参回调，选中项变化后由 notify_selection_changed()
    触发，用来刷新右侧属性面板（由 MainWindow 注册）。

    editing_locked: 处于「播放会话」时为 True —— 画布不再响应选中，主窗口禁用
    所有会改数据的按钮。点过「播放」就进入，只有「重置」会解除；「暂停」不解锁。
    """

    def __init__(self, circles=None, selected=None, on_selection_changed=None,
                 editing_locked=False):
        self.circles = default_circles() if circles is None else list(circles)
        self.selected = selected
        self.on_selection_changed = on_selection_changed
        self.editing_locked = editing_locked

    # ---------- 查询 ----------
    def current(self):
        """返回当前选中的 Circle，没有选中或下标失效时返回 None。"""
        idx = self.selected
        if idx is None or not 0 <= idx < len(self.circles):
            return None
        return self.circles[idx]

    def index_of(self, circle):
        """返回 Circle 在列表中的下标，不存在返回 None。"""
        for i, c in enumerate(self.circles):
            if c is circle:
                return i
        return None

    # ---------- 修改 ----------
    def add_circle(self, circle):
        """追加一个向量，并选中它。"""
        self.circles.append(circle)
        self.selected = len(self.circles) - 1
        return self.selected

    def remove_selected(self):
        """删除当前选中的向量，返回被删除的下标；没有选中则返回 None。"""
        idx = self.selected
        if idx is None or not 0 <= idx < len(self.circles):
            return None
        self.circles.pop(idx)

        # 颜色是按顺序绑定的，删除后自动重排 —— 不用做额外处理
        # 选中态：尽量保持相邻项被选中
        n = len(self.circles)
        if n == 0:
            self.selected = None
        else:
            self.selected = min(idx, n - 1)
        return idx

    def reset_phases(self):
        """把所有向量的相位归零。"""
        for c in self.circles:
            c.phase = 0.0

    def replace_circles(self, circles):
        """用新列表整体替换现有向量（导入时用），并清空选中项。"""
        self.circles = list(circles)
        self.selected = None

    # ---------- 通知 ----------
    def notify_selection_changed(self):
        """选中项变化后通知外部（属性面板）刷新。"""
        if self.on_selection_changed is not None:
            self.on_selection_changed()
