from __future__ import annotations
from PyQt6 import QtWidgets
import logging


class InfoDialog(QtWidgets.QDialog):
    """Explains the plan mechanism and usage workflow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log = logging.getLogger("flchemist.InfoDialog")
        self.setWindowTitle("Info \u2014 About flchemist Plans")
        self.setMinimumSize(580, 480)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("How flchemist Works")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)

        text = QtWidgets.QTextEdit()
        text.setReadOnly(True)
        text.setStyleSheet("font-size: 12px; color: #e0e0e0; background: transparent; border: none;")
        text.setHtml(self._load_content())
        layout.addWidget(text)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _load_content(self) -> str:
        from pathlib import Path
        path = Path(__file__).resolve().parent / "info_content.html"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            self._log.warning("Info content not found: %s", e)
            return "<p>Info content not found.</p>"
