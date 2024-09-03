
from qgis.PyQt import QtWidgets, uic

class StringWriterDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'string_writer_dialog_base.ui'), self)
