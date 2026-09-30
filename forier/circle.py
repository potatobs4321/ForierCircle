"""单个旋转向量（圆）的数据模型。"""


class Circle:
    """一个向量（圆）：半径 + 角速度（整数，1 = 15秒一圈）"""

    def __init__(self, radius=50.0, speed=1):
        self.radius = radius
        self.speed = speed
        self.phase = 0.0

    def __repr__(self):
        return f"Circle(radius={self.radius!r}, speed={self.speed!r})"
