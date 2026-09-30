"""绘制旋转向量、末端轨迹的 QWidget 画布。"""

import math

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QWidget

from . import config


class Canvas(QWidget):
    """把所有向量首尾相接画出来，并记录末端点形成轨迹。"""

    def __init__(self, state, parent=None):
        """
        state: AppState 实例，共享 circles / selected / on_selection_changed
        """
        super().__init__(parent)
        self.state = state
        self.trail = []
        self.max_trail = 2000
        self.setMinimumSize(600, 600)
        self.setStyleSheet("background-color: #111;")
        self.setMouseTracking(True)

        # 每帧记录每个向量的起点/终点（画布坐标），用于命中检测
        self._segments = []  # [(start QPointF, end QPointF, radius, color, idx), ...]

    # ---------- 数据访问 ----------
    @property
    def circles(self):
        return self.state.circles

    @property
    def selected(self):
        return self.state.selected

    @selected.setter
    def selected(self, v):
        self.state.selected = v

    # ---------- 坐标换算 ----------
    def _origin(self):
        """画布坐标下的原点（整条向量链的起点）。"""
        return self.width() / 3, self.height() / 2

    def _to_canvas(self, x, y):
        """模型坐标 -> 画布坐标（相对原点平移，并把 y 轴翻成屏幕方向）。"""
        ox, oy = self._origin()
        return QPointF(ox + x, oy - y)

    # ---------- 重置 / 推进 ----------
    def reset(self):
        self.trail.clear()
        self.state.reset_phases()
        self.update()

    def step(self, dt):
        x, y = 0.0, 0.0
        for c in self.circles:
            c.phase = (c.phase + c.speed * config.BASE_OMEGA * dt) % (2 * math.pi)
            x += c.radius * math.cos(c.phase)
            y += c.radius * math.sin(c.phase)

        # 轨迹存「模型坐标」（相对原点、y 轴朝上），不存画布坐标：
        # 存画布坐标的话，调整窗口大小导致原点平移后，老点还留在旧原点位置，
        # 新点已经跟着新原点走，轨迹就会被拉出一条横穿画面的直线。
        self.trail.append((x, y))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)
        self.update()

    # ---------- 命中检测 ----------
    def _hit_test(self, pos):
        """返回被点中的向量索引，没有则 None。
        命中规则：点到该向量的圆环线 或 该向量的线段 附近即算命中。
        从后往前遍历，让后面的向量优先（视觉上更靠上）。"""
        for start, end, radius, color, idx in reversed(self._segments):
            # 到向量线段的距离
            if self._dist_point_segment(pos, start, end) <= 8:
                return idx
            # 到圆环的距离
            d = math.hypot(pos.x() - start.x(), pos.y() - start.y())
            if abs(d - radius) <= 8:
                return idx
        return None

    @staticmethod
    def _dist_point_segment(p, a, b):
        ax, ay = a.x(), a.y()
        bx, by = b.x(), b.y()
        px, py = p.x(), p.y()
        dx, dy = bx - ax, by - ay
        seg_len2 = dx * dx + dy * dy
        if seg_len2 == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len2))
        cx, cy = ax + t * dx, ay + t * dy
        return math.hypot(px - cx, py - cy)

    def mousePressEvent(self, event):
        # 播放会话中不接受选中操作（点「重置」退出播放后恢复）
        if event.button() != Qt.LeftButton or self.state.editing_locked:
            return
        self.selected = self._hit_test(event.pos())  # 可能为 None，表示点空白取消选择
        self.update()
        # 通知外部（属性面板）刷新
        self.state.notify_selection_changed()

    # ---------- 绘制 ----------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        start_x, start_y = self._origin()
        cur = QPointF(start_x, start_y)

        self._segments.clear()

        for i, c in enumerate(self.circles):
            color = config.color_for(i)
            is_selected = (i == self.selected)

            # 画圆
            pen = QPen(color)
            pen.setWidth(config.CIRCLE_WIDTH_SELECTED if is_selected
                         else config.CIRCLE_WIDTH)
            if not is_selected:
                col = QColor(color)
                col.setAlpha(120)
                pen.setColor(col)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(cur, c.radius, c.radius)

            # 画向量（带箭头）
            nx = cur.x() + c.radius * math.cos(c.phase)
            ny = cur.y() - c.radius * math.sin(c.phase)
            next_pt = QPointF(nx, ny)

            pen = QPen(color)
            pen.setWidth(config.VECTOR_WIDTH_SELECTED if is_selected
                         else config.VECTOR_WIDTH)
            p.setPen(pen)
            p.drawLine(cur, next_pt)
            self._draw_arrow(p, cur, next_pt, color,
                             size=config.ARROW_SIZE_SELECTED if is_selected
                             else config.ARROW_SIZE)

            self._segments.append((QPointF(cur), QPointF(next_pt), c.radius, color, i))
            cur = next_pt

        # 末端点
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 80, 80)))
        p.drawEllipse(cur, config.END_DOT_RADIUS, config.END_DOT_RADIUS)

        # 轨迹
        if len(self.trail) > 1:
            pen = QPen(QColor(80, 255, 160))
            pen.setWidth(config.TRAIL_WIDTH)
            p.setPen(pen)
            poly = QPolygonF([self._to_canvas(x, y) for x, y in self.trail])
            p.drawPolyline(poly)

        # 末端到轨迹末端虚线
        if self.trail:
            pen = QPen(QColor(255, 255, 255, 60))
            pen.setWidth(config.DASH_WIDTH)
            pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawLine(cur, self._to_canvas(*self.trail[-1]))

    @staticmethod
    def _draw_arrow(painter, start, end, color, size=8):
        """在 end 处画一个指向 start->end 方向的箭头"""
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return
        ux, uy = dx / length, dy / length
        # 箭头底部位置
        bx = end.x() - ux * size
        by = end.y() - uy * size
        # 垂直方向
        px, py = -uy, ux
        # 两个翼点
        left = QPointF(bx + px * size * 0.5, by + py * size * 0.5)
        right = QPointF(bx - px * size * 0.5, by - py * size * 0.5)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF([end, left, right]))
