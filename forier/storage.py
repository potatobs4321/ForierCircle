"""向量的保存与导入（JSON 文件）。

文件格式（版本 1）::

    {
      "format": "forier-circle",
      "version": 1,
      "circles": [
        {"radius": 360.0, "speed": 1},
        {"radius": 150.0, "speed": 3}
      ]
    }

只保存向量的半径和角速度 —— 相位和轨迹是动画的瞬时状态，不入文件。

解析是「先全部校验成功、再交给调用方替换状态」，所以导入失败时当前画面不会
被改坏；超出可编辑范围的数值会夹紧到边界，并通过 LoadResult.warnings 告知。
"""

import json
import math
import os
import tempfile

from .circle import Circle
from .config import RADIUS_MAX, RADIUS_MIN, SPEED_MAX, SPEED_MIN

FORMAT_NAME = "forier-circle"
FORMAT_VERSION = 1

FILE_SUFFIX = ".json"
DEFAULT_FILE_NAME = "forier_circles" + FILE_SUFFIX
FILE_FILTER = "ForierCircle 向量文件 (*.json);;所有文件 (*)"


class StorageError(Exception):
    """保存或导入失败。异常信息是中文的，可以直接展示给用户。"""


class LoadResult:
    """导入结果：解析出的向量列表 + 夹紧等改动提示。"""

    def __init__(self, circles, warnings=()):
        self.circles = circles
        self.warnings = list(warnings)


# ---------- 导出 ----------
def to_dict(circles):
    """把向量列表转成可 JSON 序列化的 dict。"""
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "circles": [
            {"radius": float(c.radius), "speed": int(c.speed)} for c in circles
        ],
    }


def save(path, circles):
    """把向量列表写入 path。失败抛 StorageError。

    先写同目录下的临时文件再原子替换，避免写一半失败把原文件截断。
    """
    data = to_dict(circles)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=directory, prefix=".forier-circle-", suffix=".tmp")
    except OSError as exc:
        raise StorageError(f"无法在 {directory} 创建临时文件：{exc}") from exc

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except OSError as exc:
        raise StorageError(f"写入 {path} 失败：{exc}") from exc
    finally:
        # os.replace 成功后临时文件已经不存在，这里只清理失败残留
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ---------- 导入 ----------
def load(path):
    """读取并解析 path，返回 LoadResult。失败抛 StorageError。"""
    try:
        # utf-8-sig 同时兼容带 BOM 的文件（记事本另存为 UTF-8 时会加 BOM）
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = f.read()
    except OSError as exc:
        raise StorageError(f"无法读取 {path}：{exc}") from exc
    except UnicodeDecodeError as exc:
        raise StorageError(f"{path} 不是 UTF-8 编码的文本文件：{exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StorageError(
            f"不是合法的 JSON：第 {exc.lineno} 行第 {exc.colno} 列 {exc.msg}") from exc

    return parse(data)


def parse(data):
    """解析已经读出来的 JSON 数据，返回 LoadResult。失败抛 StorageError。"""
    if not isinstance(data, dict):
        raise StorageError("文件内容不是一个 JSON 对象，可能不是本程序保存的文件。")

    fmt = data.get("format")
    if fmt is not None and fmt != FORMAT_NAME:
        raise StorageError(f"文件里的 format 是 {fmt!r}，不是 ForierCircle 向量文件。")

    version = data.get("version", FORMAT_VERSION)
    if isinstance(version, bool) or not isinstance(version, int):
        raise StorageError(f"version 字段必须是整数，当前是 {version!r}。")
    if version > FORMAT_VERSION:
        raise StorageError(
            f"文件版本是 {version}，高于当前程序支持的版本 {FORMAT_VERSION}，请升级程序。")

    items = data.get("circles")
    if not isinstance(items, list):
        raise StorageError(
            "缺少 circles 字段，或者它不是一个数组"
            '（正确形状：{"circles": [{"radius": 100, "speed": 1}]}）。')

    circles = []
    warnings = []
    for index, item in enumerate(items, start=1):
        circle, warns = _parse_one(item, index)
        circles.append(circle)
        warnings.extend(warns)
    return LoadResult(circles, warnings)


def _parse_one(item, index):
    """解析单个向量，返回 (Circle, 提示信息列表)。"""
    if not isinstance(item, dict):
        raise StorageError(
            f"第 {index} 个向量应该是一个对象"
            f'（形如 {{"radius": 100, "speed": 1}}），当前是 {item!r}。')

    if "radius" not in item:
        raise StorageError(f"第 {index} 个向量缺少 radius 字段。")
    if "speed" not in item:
        raise StorageError(f"第 {index} 个向量缺少 speed 字段。")

    radius, warn = _parse_radius(item["radius"], index)
    speed, warn2 = _parse_speed(item["speed"], index)

    warnings = [w for w in (warn, warn2) if w]
    return Circle(radius, speed), warnings


def _parse_radius(value, index):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StorageError(f"第 {index} 个向量的 radius 必须是数字，当前是 {value!r}。")
    value = float(value)
    if not math.isfinite(value):
        raise StorageError(f"第 {index} 个向量的 radius 不是有限数字（{value}）。")

    clamped = min(max(value, RADIUS_MIN), RADIUS_MAX)
    if clamped != value:
        return clamped, (f"第 {index} 个向量的半径 {value:g} 超出 "
                         f"{RADIUS_MIN:g}~{RADIUS_MAX:g}，已夹紧为 {clamped:g}")
    return value, None


def _parse_speed(value, index):
    # JSON 里的 3.0 也当作整数 3 接受，但 3.5 这种有小数部分的要报错
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise StorageError(f"第 {index} 个向量的 speed 必须是整数，当前是 {value!r}。")

    clamped = min(max(value, SPEED_MIN), SPEED_MAX)
    if clamped != value:
        return clamped, (f"第 {index} 个向量的角速度 {value} 超出 "
                         f"{SPEED_MIN}~{SPEED_MAX}，已夹紧为 {clamped}")
    return value, None
