def classFactory(iface):
    from .main_plugin import ALModifyMonitorPlugin
    return ALModifyMonitorPlugin(iface)