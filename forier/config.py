"""全局常量：配色与角速度基准。"""

import math

from PyQt5.QtGui import QColor

# ---------- 自动分配的高区分度颜色 ----------
# 按向量下标 % len(PALETTE) 循环取用，画布和属性面板共用
PALETTE = [
    QColor("#E74C3C"),  # 红
    QColor("#1ABC9C"),  # 青
    QColor("#E67E22"),  # 橙
    QColor("#3498DB"),  # 蓝
    QColor("#F1C40F"),  # 黄
    QColor("#2ECC71"),  # 绿
    QColor("#E84393"),  # 粉
    QColor("#9B59B6"),  # 紫
]

# speed=1 -> 15秒一圈
BASE_OMEGA = 2 * math.pi / 15.0

# ---------- 属性面板可编辑范围 ----------
# 同时是保存/导入文件时的合法区间：超出该范围的值会被夹紧到边界并提示
RADIUS_MIN = 0.0
RADIUS_MAX = 500.0
SPEED_MIN = -20
SPEED_MAX = 20

# ---------- 线条粗细（画布像素） ----------
# 选中态统一画得粗一点，方便一眼看出正在编辑哪个向量
CIRCLE_WIDTH = 2             # 圆环
CIRCLE_WIDTH_SELECTED = 4
VECTOR_WIDTH = 3             # 向量线
VECTOR_WIDTH_SELECTED = 4
TRAIL_WIDTH = 3              # 末端轨迹折线
ARROW_SIZE = 10              # 向量末端箭头
ARROW_SIZE_SELECTED = 12
END_DOT_RADIUS = 5           # 末端点圆点
DASH_WIDTH = 1               # 末端点到轨迹末端的虚线


def color_for(index):
    """按向量下标取颜色，超出调色板长度则循环。"""
    return PALETTE[index % len(PALETTE)]
