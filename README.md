# ForierCircle

用一组首尾相接的旋转向量（圆）叠加，绘制傅里叶级数轨迹的 PyQt5 小工具。

## 运行

```bash
pip install -r requirements.txt
python main.py
```

以下两种方式等价（`python forier/app.py` 是 IDE 里直接右键 Run 该文件时走的路径）：

```bash
python -m forier.app
python forier/app.py
```

> 注意：`forier/` 里的模块用的是包内相对导入（如 `from .main_window import ...`），
> 请不要单独运行 `canvas.py` / `main_window.py` 等文件——它们没有 `if __name__ == "__main__"` 引导，
> 直接运行会报 `ImportError: attempted relative import with no known parent package`。
> 只有 `app.py` 和根目录的 `main.py` 是入口。

## 操作

| 操作 | 说明 |
| --- | --- |
| 播放 / 暂停 | 启停动画（每 16ms 推进一帧）；**点过播放后进入编辑锁定**，暂停不解锁 |
| 重置 | 停止播放、清空轨迹、相位归零，并**解除编辑锁定** |
| 添加向量 | 追加一个半径 120、角速度 2 的向量并自动选中 |
| 保存 | 把所有向量存成 JSON 文件（`Ctrl+S`），锁定期间仍可用 |
| 导入 | 从 JSON 文件读回向量，**替换**当前所有向量（`Ctrl+O`） |
| 点击画布 | 点中某个向量的圆环或线段即选中它；点空白处取消选中 |
| 右侧属性面板 | 修改选中向量的半径、角速度，或删除该向量 |

### 播放期间的编辑锁定

点过「播放」就进入**播放会话**，此时向量是运动中的，选中和改属性都容易出错，所以一律禁止：

| | 锁定期间 |
| --- | --- |
| 点击画布 | 不改变选中项；进入播放时选中态已清空，所以没有任何向量高亮 |
| 属性面板 | 切回提示页，显示「播放中已锁定向量编辑」 |
| 添加向量 / 导入 / 删除该向量 | 置灰不可用 |
| 保存 | **可用**（只读操作，不改当前数据） |
| 动画本身 | 照常推进，不受影响 |

- **「暂停」不解锁**：暂停只是停住画面，仍然处于播放会话中，仍然不能编辑
- **唯一的退出方式是「重置」**：它同时停止播放、清空轨迹、相位归零并恢复编辑
- **进入播放会清掉选中态**：选中态画得更粗（见下方「线条粗细」），播放中粗细不一致很扎眼，所以点「播放」时把 `selected` 一并清空。因此解锁后属性面板停在提示页，需要重新点选要编辑的向量

实现上锁定只是 `AppState.editing_locked` 一个标记：`Canvas.mousePressEvent` 开头据此直接 return，`MainWindow._set_locked()` 负责清空选中态、切换按钮可用状态和面板文案。

### 线条粗细

所有绘制尺寸集中在 `config.py`，想调粗细只改这一处：

| 常量 | 默认 | 用途 |
| --- | --- | --- |
| `CIRCLE_WIDTH` / `CIRCLE_WIDTH_SELECTED` | 2 / 4 | 圆环 |
| `VECTOR_WIDTH` / `VECTOR_WIDTH_SELECTED` | 3 / 4 | 向量线 |
| `TRAIL_WIDTH` | 3 | 末端轨迹折线 |
| `ARROW_SIZE` / `ARROW_SIZE_SELECTED` | 10 / 12 | 向量末端箭头 |
| `END_DOT_RADIUS` | 5 | 末端点圆点 |
| `DASH_WIDTH` | 1 | 末端点到轨迹末端的虚线 |

选中态用 `_SELECTED` 变体，画得更粗，方便一眼看出正在编辑哪个向量。`canvas.py` 里以 `config.XXX` 形式引用这些常量（不是 `from ... import`），所以改值会立即影响渲染。

角速度 `speed` 为整数，可为负、可为 0：`1` 表示 15 秒转一圈，`3` 表示 3 倍速，负值反向。

## 保存 / 导入

- **保存**：只写每个向量的半径和角速度；相位、轨迹是动画的瞬时状态，不入文件
- **导入**：替换当前所有向量，并清空选中项与轨迹（导入前动画若在播放则继续播放）
- **失败不改数据**：先完整解析校验，全部通过后才替换状态；任何错误只弹提示，当前画面保持原样
- **越界自动夹紧**：半径超出 `0~500`、角速度超出 `±20` 的值会夹到边界，并弹窗列出被改了哪些项
- **原子写入**：先写同目录下的临时文件再替换，写到一半失败也不会把原文件截断

文件格式：

```json
{
  "format": "forier-circle",
  "version": 1,
  "circles": [
    {"radius": 360.0, "speed": 1},
    {"radius": 150.0, "speed": 3},
    {"radius": 75.0, "speed": -5}
  ]
}
```

手写文件时的容错：`format` 和 `version` 都可省略；`speed` 写 `3.0` 也接受（等价于 `3`）但 `3.5` 会报错；带 BOM 的 UTF-8（记事本另存）能正常读取；`radius`/`speed` 缺失、类型不对、JSON 语法错误、`version` 高于程序支持的版本，都会给出指明第几个向量、哪一列的中文报错。

## 关于尺寸

初始向量为 `(半径 360, 速度 1)`、`(150, 3)`、`(75, -5)`，**半径单位就是画布像素**（绘制时没有任何缩放变换）。三者相加 585 就是末端点离原点的最远距离，所以：

- 要完整显示整条轨迹，画布大约需要 1800×1250（因为原点在 `width/3`，横向至少要 `1/3·w ≥ 585`），换算成窗口约 2100×1330 —— 1920×1080 的屏幕放不下
- 默认窗口是 1400×1000（画布约 1090×940），图形在动画过程中会有一部分超出画布被裁掉，这是已知现象
- 想让图形随窗口自动缩放、永不裁切，需要给 `Canvas.paintEvent` 引入一个 `scale` 因子并让命中检测做逆变换；`120 = 120px` 这个等价关系只在「无缩放」时成立
- 属性面板的半径/角速度上下限定义在 `config.py` 的 `RADIUS_MIN/MAX`、`SPEED_MIN/MAX`，导入文件时也用同一组范围做夹紧，想放宽只需改这一处

### 坐标系约定（改绘制代码前请先读）

`Canvas.trail` 里存的是**模型坐标**（相对原点、y 轴朝上、与画布尺寸无关），绘制时才用 `Canvas._to_canvas()` 投影成画布坐标（平移到 `(width/3, height/2)` 并翻转 y 轴）。

**不要把画布坐标存进 `trail`。** 原点依赖画布尺寸，一旦窗口大小改变，老点还留在旧原点位置、新点已经跟着新原点走，轨迹会被拉出一条横穿画面的直线，看起来就是「线条乱了」；暂停时拖动窗口还会看到轨迹和圆环彻底脱开。存模型坐标则缩放窗口时整条轨迹一起平移，形状和连续性都不受影响。

## 目录结构

```
ForierCircle/
├── main.py                 # 启动脚本：python main.py
├── requirements.txt
├── .gitignore
├── README.md
└── forier/
    ├── __init__.py         # 包导出
    ├── config.py           # 常量：PALETTE 配色、BASE_OMEGA、取值范围、线条粗细
    ├── circle.py           # Circle：单个旋转向量的数据模型
    ├── app_state.py        # AppState：共享的 circles / selected / 回调 / editing_locked
    ├── canvas.py           # Canvas：绘制向量、圆、轨迹 + 鼠标命中检测
    ├── storage.py          # JSON 保存/导入：格式定义、校验、越界夹紧提示
    ├── main_window.py      # MainWindow：按钮栏 + 画布 + 属性面板 + 定时器 + 保存/导入 + 编辑锁定
    └── app.py              # main()：创建 QApplication 并显示窗口
```

## 模块依赖

```
app.py ──> main_window.py ──┬──> app_state.py ──> circle.py
                            ├──> canvas.py ─────┐
                            ├──> storage.py ────┼──> config.py
                            └──> config.py      └──> circle.py
```

`config.py` 只依赖 PyQt5 的 `QColor`；`app_state.py` 和 `storage.py` 都不依赖任何 UI 控件、也不需要 `QApplication`，可以脱离界面单独调用（例如直接 `from forier import storage; storage.load("x.json")`）。
