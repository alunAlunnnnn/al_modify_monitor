from qgis.PyQt.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
                                 QPushButton, QListWidget, QListWidgetItem,
                                 QComboBox, QLabel, QCheckBox, QLineEdit, QScrollArea, QGroupBox)
from qgis.PyQt.QtCore import Qt


class ALMonitorDockWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("AL Modify Monitor", parent)
        dock_area = getattr(Qt, 'DockWidgetArea', Qt)
        self.setAllowedAreas(dock_area.LeftDockWidgetArea | dock_area.RightDockWidgetArea)

        # 主容器
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)

        # 1. 状态控制区
        self.toggle_btn = QPushButton("启动追踪 (Start Tracking)")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setStyleSheet(
            "QPushButton:checked { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.main_layout.addWidget(self.toggle_btn)

        # 2. 字段设置区
        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel("状态字段名:"))
        self.combo_field = QComboBox()
        self.combo_field.setEditable(True)
        self.combo_field.setPlaceholderText("留空则默认使用 al_checked")
        field_layout.addWidget(self.combo_field)
        self.main_layout.addLayout(field_layout)

        # ==================== 修改后 ====================
        # 3. 图层选择区 (带水平布局与刷新按钮)
        layer_header_layout = QHBoxLayout()
        layer_header_layout.addWidget(QLabel("选择要追踪的矢量图层:"))
        layer_header_layout.addStretch()  # 弹簧，把按钮推到最右侧

        self.btn_refresh = QPushButton("刷新图层")  # 新增的刷新按钮
        # 给按钮一点样式，让它看起来更精致小巧
        self.btn_refresh.setStyleSheet("QPushButton { padding: 2px 8px; }")
        layer_header_layout.addWidget(self.btn_refresh)

        self.main_layout.addLayout(layer_header_layout)

        self.list_layers = QListWidget()
        self.main_layout.addWidget(self.list_layers)

        # 4. 快捷键配置区 (1~0)
        self.group_hotkeys = QGroupBox("快捷键配置 (仅对当前激活图层生效)")
        hotkey_layout = QVBoxLayout()
        self.hotkey_configs = {}  # 存储快捷键UI组件的字典

        # 动态生成 1 到 0 的配置项
        keys = [str(i) for i in range(1, 10)] + ['0']
        for k in keys:
            row_layout = QHBoxLayout()
            chk_enable = QCheckBox(f"按键 {k}")
            chk_enable.setChecked(k in ['1', '2'])  # 默认开启 1 和 2

            row_layout.addWidget(chk_enable)
            row_layout.addWidget(QLabel("写入值:"))

            line_val = QLineEdit()
            # 默认值逻辑：1->1, 2->0, 其它->按键本身数字
            default_val = '1' if k == '1' else ('0' if k == '2' else k)
            line_val.setText(default_val)
            line_val.setMaximumWidth(80)
            row_layout.addWidget(line_val)

            hotkey_layout.addLayout(row_layout)
            self.hotkey_configs[k] = {'checkbox': chk_enable, 'lineedit': line_val}

        self.group_hotkeys.setLayout(hotkey_layout)

        # 使用 ScrollArea 包裹快捷键，防止小屏幕显示不全
        scroll = QScrollArea()
        scroll.setWidget(self.group_hotkeys)
        scroll.setWidgetResizable(True)
        self.main_layout.addWidget(scroll)

        self.setWidget(self.main_widget)