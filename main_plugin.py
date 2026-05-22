from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsMapLayer
from qgis.utils import iface
from .dock_widget import ALMonitorDockWidget
from .tracker_logic import TrackerEngine


class ALModifyMonitorPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = None
        self.action = None
        self.dock = None
        self.engine = TrackerEngine()

    def initGui(self):
        """挂载 UI 到 QGIS"""
        # 创建菜单栏和工具栏动作
        self.action = QAction("AL Modify Monitor", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu("AL Modify Monitor", self.action)

        # 初始化 Dock 且隐藏
        self.dock = ALMonitorDockWidget()
        dock_area = getattr(Qt, 'DockWidgetArea', Qt)
        self.iface.addDockWidget(dock_area.RightDockWidgetArea, self.dock)
        self.dock.hide()

        # 绑定 UI 交互信号
        self.dock.toggle_btn.clicked.connect(self.on_toggle_clicked)
        self.dock.list_layers.itemClicked.connect(self.populate_fields)

        # 绑定 QGIS 工程生命周期 (规则 5: 完美生命周期)
        QgsProject.instance().layersRemoved.connect(self.on_layers_removed)
        QgsProject.instance().cleared.connect(self.on_project_cleared)
        QgsProject.instance().layersAdded.connect(self.refresh_layer_list)

    def unload(self):
        """插件卸载/QGIS关闭时的终极清理：防止崩溃"""
        self.engine.stop_all()  # 断开所有底层信号

        # 断开全局生命周期信号
        try:
            QgsProject.instance().layersRemoved.disconnect(self.on_layers_removed)
            QgsProject.instance().cleared.disconnect(self.on_project_cleared)
            QgsProject.instance().layersAdded.disconnect(self.refresh_layer_list)
        except TypeError:
            pass

        # 移除 UI 组件
        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
        if self.action:
            self.iface.removePluginVectorMenu("AL Modify Monitor", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        """点击菜单项时展开/隐藏 Dock，并刷新图层列表"""
        if self.dock.isVisible():
            self.dock.hide()
        else:
            self.refresh_layer_list()
            self.dock.show()

    def refresh_layer_list(self, _=None):
        """抓取工程中所有矢量图层填充至列表"""
        if self.dock.toggle_btn.isChecked():
            return

        self.dock.list_layers.clear()

        # 兼容 Qt5/6 的强类型枚举
        item_flag = getattr(Qt, 'ItemFlag', Qt)
        check_state = getattr(Qt, 'CheckState', Qt)
        data_role = getattr(Qt, 'ItemDataRole', Qt)

        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                item = __import__('qgis.PyQt.QtWidgets').PyQt.QtWidgets.QListWidgetItem(layer.name())
                item.setFlags(item.flags() | item_flag.ItemIsUserCheckable)
                item.setCheckState(check_state.Unchecked)
                item.setData(data_role.UserRole, layer.id())
                self.dock.list_layers.addItem(item)

    def populate_fields(self, item):
        """点击图层列表项时，读取对应图层字段到下拉框"""
        data_role = getattr(Qt, 'ItemDataRole', Qt)  # 兼容代码
        layer_id = item.data(data_role.UserRole)
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            self.dock.combo_field.clear()
            self.dock.combo_field.addItems([f.name() for f in layer.fields()])

    def on_toggle_clicked(self):
        """点击启动/停止按钮的主逻辑"""
        is_running = self.dock.toggle_btn.isChecked()
        check_state = getattr(Qt, 'CheckState', Qt)  # 兼容代码
        data_role = getattr(Qt, 'ItemDataRole', Qt)  # 兼容代码

        if is_running:
            hotkeys = {}
            for k, cfg in self.dock.hotkey_configs.items():
                if cfg['checkbox'].isChecked():
                    val = cfg['lineedit'].text().strip()
                    if val: hotkeys[k] = val

            target_layers = []
            for i in range(self.dock.list_layers.count()):
                item = self.dock.list_layers.item(i)
                # 使用兼容的 check_state
                if item.checkState() == check_state.Checked:
                    # 使用兼容的 data_role
                    layer = QgsProject.instance().mapLayer(item.data(data_role.UserRole))
                    if layer: target_layers.append(layer)

            if not target_layers:
                self.iface.messageBar().pushWarning("提示", "请至少勾选一个图层进行追踪。")
                self.dock.toggle_btn.setChecked(False)
                return

            field_name = self.dock.combo_field.currentText()

            # 启动引擎
            self.engine.configure_hotkeys(hotkeys)
            count = self.engine.start_tracking(target_layers, field_name)

            self.dock.toggle_btn.setText("停止追踪 (Stop Tracking)")
            self.iface.messageBar().pushSuccess("追踪启动", f"成功挂载 {count} 个图层的动态追踪与全局热键。")
            self.dock.list_layers.setEnabled(False)  # 运行时锁定 UI 防呆
            self.dock.group_hotkeys.setEnabled(False)

        else:
            self.engine.stop_all()
            self.dock.toggle_btn.setText("启动追踪 (Start Tracking)")
            self.dock.list_layers.setEnabled(True)
            self.dock.group_hotkeys.setEnabled(True)
            self.iface.messageBar().pushInfo("追踪停止", "已安全解绑所有监控信号。")

    def on_layers_removed(self, layer_ids):
        """生命周期钩子：图层被删时解绑"""
        for lid in layer_ids:
            self.engine.remove_layer_tracking(lid)

    def on_project_cleared(self):
        """生命周期钩子：新建工程时完全停止"""
        if self.dock.toggle_btn.isChecked():
            self.dock.toggle_btn.click()  # 模拟点击触发完整停止流程
        self.dock.list_layers.clear()