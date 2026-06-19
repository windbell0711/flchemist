from __future__ import annotations
from PyQt6 import QtWidgets, QtCore, QtGui


class ErrorChoiceDialog(QtWidgets.QDialog):
    """Dialog shown when an action fails during execution."""
    decision_made = QtCore.pyqtSignal(str)

    def __init__(self, index: int, desc: str, error: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Action Failed")
        self.setMinimumSize(520, 280)
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel(f"<b>Action #{index} failed</b>")
        layout.addWidget(title)

        layout.addWidget(QtWidgets.QLabel(f"Operation: {desc}"))

        text = QtWidgets.QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(error)
        text.setMaximumHeight(100)
        layout.addWidget(text)

        layout.addWidget(QtWidgets.QLabel("Choose how to proceed:"))

        # Row 1: Ignore, Ignore All
        row1 = QtWidgets.QHBoxLayout()
        btn_ignore = QtWidgets.QPushButton("Ignore")
        btn_ignore.setToolTip("Skip this action and continue execution")
        btn_ignore.clicked.connect(lambda: self._done("ignore"))
        btn_ignore.setObjectName("accent-button")
        row1.addWidget(btn_ignore)

        btn_ignore_all = QtWidgets.QPushButton("Ignore All")
        btn_ignore_all.setToolTip("Skip all remaining failed actions automatically")
        btn_ignore_all.clicked.connect(lambda: self._done("ignore_all"))
        btn_ignore_all.setObjectName("accent-button")
        row1.addWidget(btn_ignore_all)
        layout.addLayout(row1)

        # Row 2: Abort, Rollback All
        row2 = QtWidgets.QHBoxLayout()
        btn_abort = QtWidgets.QPushButton("Abort")
        btn_abort.setToolTip("Rollback this action and stop execution")
        btn_abort.clicked.connect(lambda: self._done("abort"))
        btn_abort.setObjectName("accent-button")
        row2.addWidget(btn_abort)

        btn_rollback = QtWidgets.QPushButton("Rollback All")
        btn_rollback.setToolTip("Rollback all completed actions and stop")
        btn_rollback.clicked.connect(lambda: self._done("rollback_all"))
        btn_rollback.setObjectName("accent-button")
        row2.addWidget(btn_rollback)
        layout.addLayout(row2)

    def _done(self, decision: str):
        self.decision_made.emit(decision)
        self.accept()
