from qgis.core import (QgsProject, QgsVectorLayer, QgsField, QgsMessageLog,
                       QgsWkbTypes, QgsSymbol, QgsRendererCategory,
                       QgsCategorizedSymbolRenderer)
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QShortcut
from qgis.PyQt.QtGui import QKeySequence, QColor
from qgis.PyQt.QtCore import Qt

# 跨 Qt5/Qt6 获取底层类型兼容方案
try:
    from qgis.PyQt.QtCore import QMetaType

    INT_TYPE = QMetaType.Type.Int
    STRING_TYPE = QMetaType.Type.QString
except AttributeError:
    from qgis.PyQt.QtCore import QVariant

    INT_TYPE = QVariant.Int
    STRING_TYPE = QVariant.String


class TrackerEngine:
    def __init__(self):
        self.tracked_data = {}  # {layer_id: {'layer': QgsVectorLayer, 'field_idx': int}}
        self.shortcuts = []
        self.hotkey_settings = {}  # { '1': '1', '2': '0', ... }

    def configure_hotkeys(self, hotkey_dict):
        """挂载快捷键逻辑"""
        self._clear_shortcuts()
        self.hotkey_settings = hotkey_dict

        main_window = iface.mainWindow()
        # 兼容 Qt5/6 的上下文环境
        context = getattr(Qt, 'ApplicationShortcut', None)
        if context is None:
            context = Qt.ShortcutContext.ApplicationShortcut

        for key, val in hotkey_dict.items():
            sc = QShortcut(QKeySequence(key), main_window)
            sc.setContext(context)
            # 闭包绑定当前 key 的值
            sc.activated.connect(lambda v=val: self.apply_hotkey_override(v))
            self.shortcuts.append(sc)

    def _clear_shortcuts(self):
        for sc in self.shortcuts:
            sc.setEnabled(False)
            sc.deleteLater()
        self.shortcuts.clear()

    def start_tracking(self, layers, target_field):
        """批量启动图层追踪，处理字段异构"""
        if not target_field.strip():
            target_field = "al_checked"

        success_count = 0
        for layer in layers:
            field_name = target_field
            field_idx = layer.fields().indexOf(field_name)

            # 异构验证逻辑
            if field_idx != -1:
                f_type = layer.fields().at(field_idx).type()
                # 如果存在的字段不是数字也不是字符串（比如是日期或Blob），则降级使用 al_checked
                if f_type not in [INT_TYPE, STRING_TYPE]:
                    iface.messageBar().pushWarning(
                        "字段异构冲突",
                        f"图层 '{layer.name()}' 中的 '{field_name}' 类型不兼容，将自动使用 'al_checked' 替代。"
                    )
                    field_name = "al_checked"
                    field_idx = layer.fields().indexOf(field_name)

            # 字段不存在时的创建逻辑
            if field_idx == -1:
                was_editing = layer.isEditable()
                if was_editing: layer.commitChanges()

                new_field = QgsField(field_name, INT_TYPE)
                layer.dataProvider().addAttributes([new_field])
                layer.updateFields()
                field_idx = layer.fields().indexOf(field_name)

                # 初始化为 0
                layer.startEditing()
                layer.beginEditCommand(f"初始化 {field_name}")
                for f in layer.getFeatures():
                    layer.changeAttributeValue(f.id(), field_idx, 0)
                layer.endEditCommand()
                layer.commitChanges()

                if was_editing: layer.startEditing()

            # 注册监听
            layer.geometryChanged.connect(self._on_geometry_changed)
            self.tracked_data[layer.id()] = {'layer': layer, 'field_idx': field_idx}

            self._apply_categorized_symbology(layer, field_name)
            success_count += 1

        return success_count

    def stop_all(self):
        """全量释放资源（生命周期安全出口）"""
        for lid, data in self.tracked_data.items():
            layer = data['layer']
            try:
                layer.geometryChanged.disconnect(self._on_geometry_changed)
            except (TypeError, RuntimeError):
                pass  # 图层已被销毁或信号已断开时安全忽略
        self.tracked_data.clear()
        self._clear_shortcuts()

    def remove_layer_tracking(self, layer_id):
        """当工程中图层被删除时安全剥离"""
        if layer_id in self.tracked_data:
            data = self.tracked_data.pop(layer_id)
            try:
                data['layer'].geometryChanged.disconnect(self._on_geometry_changed)
            except:
                pass

    def _on_geometry_changed(self, fid, geom):
        """自动监听核心：寻找触发信号的图层"""
        # 由于 PyQGIS 信号中不包含 sender，我们通过遍历寻找激活状态的图层
        # 对于单一要素编辑，这通常是 activeLayer
        active_layer = iface.activeLayer()
        if not active_layer or active_layer.id() not in self.tracked_data:
            return

        if active_layer.isEditable():
            f_idx = self.tracked_data[active_layer.id()]['field_idx']
            active_layer.changeAttributeValue(fid, f_idx, 1)

    def apply_hotkey_override(self, val_str):
        """快捷键覆写逻辑：严格归属于当前上下文"""
        active_layer = iface.activeLayer()

        # 规则 4: 未勾选追踪的激活图层，拒绝操作并弹出 Message
        if not active_layer or active_layer.id() not in self.tracked_data:
            iface.messageBar().pushInfo("AL Modify Monitor", "当前激活的图层未加入追踪列表，操作已忽略。")
            return

        if not active_layer.isEditable():
            iface.messageBar().pushWarning("AL Modify Monitor", "当前图层未开启编辑模式，无法修改属性。")
            return

        selected_fids = active_layer.selectedFeatureIds()
        if not selected_fids:
            return

        f_idx = self.tracked_data[active_layer.id()]['field_idx']

        # 尝试转为数字，以适应整型字段
        try:
            val = int(val_str)
        except ValueError:
            val = val_str

        active_layer.beginEditCommand(f"快捷键状态校准 ({val})")
        for fid in selected_fids:
            active_layer.changeAttributeValue(fid, f_idx, val)
        active_layer.endEditCommand()
        active_layer.triggerRepaint()

    def _apply_categorized_symbology(self, layer, field_name):
        """自动检测 Single Symbol 并转换为分类符号 (Categorized)"""
        # 1. 拦截：仅处理单一符号的图层
        if layer.renderer().type() != 'singleSymbol':
            return

        # 2. 提取需要创建分类的所有值 (去重)，确保至少有我们追踪的值
        tracked_values = set(self.hotkey_settings.values())

        categories = []
        geom_type = layer.geometryType()

        # 兼容 Qt5/6 的无填充枚举 (用于面状数据透明)
        brush_style = getattr(Qt, 'BrushStyle', Qt)

        for val_str in tracked_values:
            # 尝试转为整型以匹配数据库类型
            try:
                val = int(val_str)
            except ValueError:
                val = val_str

            # 创建基于几何类型的默认符号
            symbol = QgsSymbol.defaultSymbol(geom_type)
            if not symbol:
                continue

            # 3. 颜色映射逻辑 (1=绿, 0=红, 其他=蓝色系作为备选)
            if val_str == '1':
                color = QColor(0, 255, 0)  # 纯绿
            elif val_str == '0':
                color = QColor(255, 0, 0)  # 纯红
            else:
                color = QColor(0, 150, 255)  # 其他值为亮蓝色

            # 4. 根据几何类型精细化样式
            if geom_type == QgsWkbTypes.PolygonGeometry:
                # 面要素：无填充，仅改变轮廓颜色，加粗轮廓
                layer_sym = symbol.symbolLayer(0)
                layer_sym.setBrushStyle(brush_style.NoBrush)
                layer_sym.setStrokeColor(color)
                layer_sym.setStrokeWidth(0.66)  # 稍微加粗让用户更容易看清
            else:
                # 点/线要素：直接改变主颜色
                symbol.setColor(color)
                if geom_type == QgsWkbTypes.LineGeometry:
                    symbol.symbolLayer(0).setWidth(0.66)

            # 创建该分类
            category = QgsRendererCategory(val, symbol, str(val))
            categories.append(category)

        # 5. 添加一个兜底的默认分类 (其他所有未匹配的值)
        default_symbol = QgsSymbol.defaultSymbol(geom_type)
        if geom_type == QgsWkbTypes.PolygonGeometry:
            default_symbol.symbolLayer(0).setBrushStyle(brush_style.NoBrush)
            default_symbol.symbolLayer(0).setStrokeColor(QColor(150, 150, 150))  # 灰色轮廓
        else:
            default_symbol.setColor(QColor(150, 150, 150))

        categories.append(QgsRendererCategory("", default_symbol, "其他/未标记"))

        # 6. 生成并应用分类渲染器
        renderer = QgsCategorizedSymbolRenderer(field_name, categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()