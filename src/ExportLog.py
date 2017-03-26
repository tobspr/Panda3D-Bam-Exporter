

import sys

import bpy
from bpy.props import StringProperty


class ExportLog(object):
    """ Class which tracks warnings and errors during export """

    WARNING = "Warning"
    ERROR = "Error"

    MESSAGE_SEPERATOR = "\n"
    SEVERITY_DIVIDER = "|#|"

    EXPORTED_MESSAGE_QUEUE = []

    def __init__(self):
        self._message_queue = []

    def info(self, *args):
        """ Adds a new info, this will not be logged but just printed to stdout """
        print("Info:", *args)

    def warning(self, *args):
        """ Adds a new warning to the log """
        self._add_entry(self.WARNING, *args)

    def error(self, *args):
        """ Adds a new error to the log """
        self._add_entry(self.ERROR, *args)

    def _add_entry(self, severity, *args):
        """ Internal method to append a new entry to the message queue """
        content = ' '.join([str(i) for i in args])
        self._message_queue.append((severity, content))
        print(severity + ":", content, file=sys.stderr)

    def report(self):
        """ Shows a dialog with all warnings and errors, but only in case
        there were some """
        
        if self._message_queue:
            ExportLog.EXPORTED_MESSAGE_QUEUE = self._message_queue
            bpy.ops.pbe_export.status()

class OperatorExportStatus(bpy.types.Operator):
    bl_idname = "pbe_export.status"
    bl_label = "Export Status"
 
    def execute(self, context):
        wm = context.window_manager
        return wm.invoke_popup(self, width=800, height=400)
 
    def draw(self, context):
        self.layout.row().label("Export status:")
        self.layout.row()
        for severity, message in ExportLog.EXPORTED_MESSAGE_QUEUE:
            row = self.layout.row()
            message = message.replace("\n", "")
            row.label(message, icon="CANCEL" if severity == ExportLog.ERROR else "ERROR")

        self.layout.row()

def register():
    bpy.utils.register_class(OperatorExportStatus)
    #bpy.utils.register_class(OperatorExportStatusOk)


def unregister():
    bpy.utils.unregister_class(OperatorExportStatus)
    #bpy.utils.unregister_class(OperatorExportStatusOk)
