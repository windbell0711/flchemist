from __future__ import annotations
from pathlib import Path

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


class ApiConfigDialog(QtWidgets.QDialog):
    """Configure API key and base URL for AI features."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._env_path = Path(__file__).resolve().parent.parent / ".env"
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        self.setWindowTitle("API Configuration")
        self.setMinimumSize(520, 280)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("API Configuration")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Configure the API key and endpoint for AI-generated plans."
        )
        subtitle.setStyleSheet("font-size: 11px; color: #888888; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # API Key
        key_label = QtWidgets.QLabel("API Key:")
        key_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(key_label)

        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setPlaceholderText("sk-...")
        layout.addWidget(self.key_input)

        # Base URL
        url_label = QtWidgets.QLabel("Base URL:")
        url_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(url_label)

        self.url_input = QtWidgets.QLineEdit()
        self.url_input.setPlaceholderText("https://api.deepseek.com")
        layout.addWidget(self.url_input)

        # Status
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.btn_save = QtWidgets.QPushButton("Save")
        self.btn_save.setObjectName("accent-button")
        self.btn_save.clicked.connect(self._save_config)
        btn_row.addWidget(self.btn_save)

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _load_config(self):
        if not self._env_path.exists():
            return
        for line in self._env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                self.key_input.setText(line.split("=", 1)[1])
            elif line.startswith("OPENAI_BASE_URL="):
                self.url_input.setText(line.split("=", 1)[1])

    def _save_config(self):
        key = self.key_input.text().strip()
        url = self.url_input.text().strip()
        if not key:
            QtWidgets.QMessageBox.warning(self, "Missing Key", "API Key is required.")
            return

        lines = []
        found_key = found_url = False
        if self._env_path.exists():
            for line in self._env_path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY="):
                    lines.append(f"DEEPSEEK_API_KEY={key}")
                    found_key = True
                elif line.strip().startswith("OPENAI_BASE_URL="):
                    if url:
                        lines.append(f"OPENAI_BASE_URL={url}")
                    found_url = True
                else:
                    lines.append(line)
        if not found_key:
            lines.append(f"DEEPSEEK_API_KEY={key}")
        if url and not found_url:
            lines.append(f"OPENAI_BASE_URL={url}")

        self._env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.status_label.setText("Saved successfully!")
        self.status_label.setStyleSheet("font-size: 11px; color: #4caf50;")
        QtCore.QTimer.singleShot(1500, self.accept)
        self.btn_save.setEnabled(False)
