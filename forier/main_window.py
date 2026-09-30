"""主窗口：顶部按钮栏 + 画布 + 右侧属性面板。"""

import os

from PyQt5.QtCore import QDateTime, Qt, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QShortcut, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget,
)

from . import storage
from .app_state import AppState
from .canvas import Canvas
from .circle import Circle
from .config import RADIUS_MAX, RADIUS_MIN, SPEED_MAX, SPEED_MIN, color_for

# 点击「添加向量」时新建向量的默认参数（跟默认向量同量级，否则新向量看着像个点）
NEW_CIRCLE_RADIUS = 120.0
NEW_CIRCLE_SPEED = 2

# 导入提示里最多列几条夹紧信息，其余折叠成「还有 N 条」
MAX_WARNINGS_SHOWN = 8

# 右侧提示页的两种文案
HINT_TEXT = "点击画布上的向量进行编辑"
LOCKED_HINT_TEXT = ("播放中已锁定向量编辑\n\n"
                    "点「重置」退出播放并恢复编辑")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("傅里叶动图 - PyQt5")

        # 共享状态
        self.state = AppState(on_selection_changed=self._refresh_property_panel)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 顶部按钮栏
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        self.play_btn = QPushButton("播放")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self._toggle_play)
        top_bar.addWidget(self.play_btn)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setToolTip("停止播放、清空轨迹、相位归零，并解除编辑锁定")
        self.reset_btn.clicked.connect(self._reset_all)
        top_bar.addWidget(self.reset_btn)

        self.add_btn = QPushButton("添加向量")
        self.add_btn.clicked.connect(self._add_circle)
        top_bar.addWidget(self.add_btn)

        # 文件操作分成独立一组，和上面的编辑操作拉开一点距离
        top_bar.addSpacing(20)

        self.import_btn = QPushButton("导入")
        self.import_btn.setToolTip("从 JSON 文件导入向量，替换当前所有向量 (Ctrl+O)")
        self.import_btn.clicked.connect(self._import_vectors)
        top_bar.addWidget(self.import_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.setToolTip("把当前所有向量保存到 JSON 文件 (Ctrl+S)")
        self.save_btn.clicked.connect(self._save_vectors)
        top_bar.addWidget(self.save_btn)

        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        # 主体：画布 + 右侧属性面板
        body = QHBoxLayout()
        self.canvas = Canvas(self.state)
        body.addWidget(self.canvas, stretch=3)

        # 右侧属性面板：用 QStackedWidget 切换「提示页」/「编辑页」
        self.prop_panel = QWidget()
        self.prop_panel.setFixedWidth(280)
        prop_layout = QVBoxLayout(self.prop_panel)

        self.prop_stack = QStackedWidget()
        prop_layout.addWidget(self.prop_stack)

        # 页 0：提示
        self.hint_page = QWidget()
        hint_layout = QVBoxLayout(self.hint_page)
        self.hint_label = QLabel(HINT_TEXT)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: #888; font-size: 14px;")
        hint_layout.addWidget(self.hint_label)
        self.prop_stack.addWidget(self.hint_page)

        # 页 1：属性编辑
        self.edit_page = QGroupBox("向量属性")
        edit_layout = QFormLayout(self.edit_page)

        self.title_label = QLabel()
        edit_layout.addRow(self.title_label)

        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(RADIUS_MIN, RADIUS_MAX)
        self.radius_spin.valueChanged.connect(self._on_radius_changed)
        edit_layout.addRow("半径:", self.radius_spin)

        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(SPEED_MIN, SPEED_MAX)
        self.speed_spin.setToolTip("1 = 15秒转一圈；整数，可负可0")
        self.speed_spin.valueChanged.connect(self._on_speed_changed)
        edit_layout.addRow("角速度:", self.speed_spin)

        self.del_btn = QPushButton("删除该向量")
        self.del_btn.clicked.connect(self._delete_selected)
        edit_layout.addRow(self.del_btn)

        self.prop_stack.addWidget(self.edit_page)

        body.addWidget(self.prop_panel, stretch=0)
        main_layout.addLayout(body, stretch=1)

        # 定时器
        self.timer = QTimer()
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self._last_ms = None

        # 上次保存/导入用过的路径，作为下次文件对话框的起始位置
        self._last_path = None

        for key, slot in ((QKeySequence.Save, self._save_vectors),
                          (QKeySequence.Open, self._import_vectors)):
            shortcut = QShortcut(key, self)
            shortcut.activated.connect(slot)

        # 默认向量半径之和 585px，画布原点在 (width/3, height/2)，
        # 要完整显示轨迹大约需要画布 1800x1250（屏幕放不下），
        # 这里给一个尽量大的常用尺寸；屏幕更小时窗口管理器会自动缩小。
        self.resize(1400, 1000)
        self._set_locked(False)

    # ---------- 播放控制 ----------
    def _toggle_play(self, playing):
        if playing:
            self.play_btn.setText("暂停")
            self._last_ms = None
            self.timer.start()
            self._set_locked(True)  # 进入播放会话：锁定编辑
        else:
            self.play_btn.setText("播放")
            self.timer.stop()
            # 注意：暂停不解锁，锁定会一直持续到点「重置」

    def _reset_all(self):
        """重置：停止播放、清空轨迹、相位归零，并解除编辑锁定。"""
        self.canvas.reset()
        self.play_btn.setChecked(False)  # 触发 _toggle_play(False) 停掉定时器
        self._set_locked(False)

    def _set_locked(self, locked):
        """锁定/解锁编辑。

        锁定期间画布不响应选中，所有会改数据的按钮禁用；「保存」是只读操作，
        保持可用。

        进入锁定时会清掉选中态 —— 选中态画得更粗，播放中粗细不一致很扎眼；
        所以解锁后属性面板停在提示页，需要重新点选要编辑的向量。
        """
        self.state.editing_locked = locked
        if locked:
            self.state.selected = None
        for btn in (self.add_btn, self.import_btn, self.del_btn):
            btn.setEnabled(not locked)
        self.hint_label.setText(LOCKED_HINT_TEXT if locked else HINT_TEXT)
        self._refresh_property_panel()

    def _tick(self):
        now = QDateTime.currentMSecsSinceEpoch()
        if self._last_ms is None:
            dt = 0.016
        else:
            dt = (now - self._last_ms) / 1000.0
        self._last_ms = now
        dt = min(dt, 0.05)
        self.canvas.step(dt)

    # ---------- 增删改 ----------
    def _add_circle(self):
        self.state.add_circle(Circle(NEW_CIRCLE_RADIUS, NEW_CIRCLE_SPEED))
        self.canvas.update()
        self._refresh_property_panel()

    def _delete_selected(self):
        if self.state.remove_selected() is None:
            return
        self.canvas.trail.clear()
        self.canvas.update()
        self._refresh_property_panel()

    def _on_radius_changed(self, v):
        c = self.state.current()
        if c is not None:
            c.radius = v
            self.canvas.update()

    def _on_speed_changed(self, v):
        c = self.state.current()
        if c is not None:
            c.speed = v

    # ---------- 属性面板刷新 ----------
    def _refresh_property_panel(self):
        if self.state.editing_locked:
            # 锁定期间统一停在提示页，上面写清了为什么不能编辑
            self.prop_stack.setCurrentIndex(0)
            return

        c = self.state.current()
        if c is None:
            self.prop_stack.setCurrentIndex(0)
            return

        idx = self.state.selected
        color = color_for(idx)

        self.prop_stack.setCurrentIndex(1)
        self.title_label.setText(
            f"<b style='color:{color.name()}'>向量 #{idx + 1}</b>"
        )
        # 用 blockSignals 避免设置值时触发回调
        self.radius_spin.blockSignals(True)
        self.radius_spin.setValue(c.radius)
        self.radius_spin.blockSignals(False)

        self.speed_spin.blockSignals(True)
        self.speed_spin.setValue(c.speed)
        self.speed_spin.blockSignals(False)

    # ---------- 保存 / 导入 ----------
    def _dialog_start_path(self):
        """文件对话框的起始位置：优先上次用过的路径，否则当前工作目录。"""
        return self._last_path or os.getcwd()

    def _save_vectors(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存向量", self._dialog_start_path(), storage.FILE_FILTER)
        if not path:
            return  # 用户取消

        if not os.path.splitext(path)[1]:
            path += storage.FILE_SUFFIX

        try:
            storage.save(path, self.state.circles)
        except storage.StorageError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return

        self._last_path = path
        self.statusBar().showMessage(
            f"已保存 {len(self.state.circles)} 个向量到 {path}", 5000)

    def _import_vectors(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入向量", self._dialog_start_path(), storage.FILE_FILTER)
        if not path:
            return  # 用户取消

        # 先完整解析，成功后才动当前数据；失败时画面保持不变
        try:
            result = storage.load(path)
        except storage.StorageError as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return

        self._last_path = path
        self._apply_loaded(result, path)

    def _apply_loaded(self, result, path):
        """把导入结果套用到界面上。"""
        self.state.replace_circles(result.circles)
        self.canvas.trail.clear()
        self.canvas.update()
        self._refresh_property_panel()

        summary = f"已从 {os.path.basename(path)} 导入 {len(result.circles)} 个向量"
        if result.warnings:
            QMessageBox.information(
                self, "导入完成（部分数值已调整）",
                summary + "\n\n" + self._format_warnings(result.warnings))
        else:
            self.statusBar().showMessage(summary, 5000)

    @staticmethod
    def _format_warnings(warnings):
        """夹紧信息太多时折叠，避免弹窗长到看不完。"""
        shown = warnings[:MAX_WARNINGS_SHOWN]
        if len(warnings) > MAX_WARNINGS_SHOWN:
            shown.append(f"……还有 {len(warnings) - MAX_WARNINGS_SHOWN} 条同类调整")
        return "\n".join(shown)
