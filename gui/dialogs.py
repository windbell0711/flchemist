# dialogs.py
from __future__ import annotations
from PyQt6 import QtWidgets, QtCore, QtGui
from gui.models import ExecuteDecision

class ErrorChoiceDialog(QtWidgets.QDialog):
    """Dialog shown when an action fails during execution."""
    decision_made = QtCore.pyqtSignal(str)

    def __init__(self, index: int, desc: str, error: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u64cd\u4f5c\u5931\u8d25")
        self.setMinimumSize(500, 250)
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel(
            f"<b>\u7b2c {index} \u4e2a\u64cd\u4f5c\u6267\u884c\u5931\u8d25</b>"
        )
        layout.addWidget(title)

        # Description
        layout.addWidget(QtWidgets.QLabel(f"\u64cd\u4f5c: {desc}"))

        # Error detail
        text = QtWidgets.QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(error)
        text.setMaximumHeight(100)
        layout.addWidget(text)

        layout.addWidget(QtWidgets.QLabel("\u8bf7\u9009\u62e9\u5982\u4f55\u5904\u7406:"))

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_abort = QtWidgets.QPushButton("\u4e2d\u6b62\u5f53\u524d\u64cd\u4f5c")
        btn_abort.setToolTip("\u56de\u6eda\u8fd9\u4e00\u4e2a\u64cd\u4f5c\uff0c\u7136\u540e\u505c\u6b62\u6267\u884c")
        btn_abort.clicked.connect(lambda: self._done("abort"))

        btn_rollback = QtWidgets.QPushButton("\u5168\u90e8\u56de\u6eda")
        btn_rollback.setToolTip("\u56de\u6eda\u6240\u6709\u5df2\u5b8c\u6210\u7684\u64cd\u4f5c\uff0c\u7136\u540e\u505c\u6b62\u6267\u884c")
        btn_rollback.clicked.connect(lambda: self._done("rollback_all"))

        btn_layout.addWidget(btn_abort)
        btn_layout.addWidget(btn_rollback)
        layout.addLayout(btn_layout)

    def _done(self, decision: str):
        self.decision_made.emit(decision)
        self.accept()
