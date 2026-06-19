from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

from PyQt6 import QtWidgets, QtCore

from gui.session import Session
from gui.workers import PlanReverseWorker


class RevertDialog(QtWidgets.QDialog):
    """Reverse the currently loaded plan's actions in reverse order."""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._log = logging.getLogger("flchemist.RevertDialog")
        self._setup_ui()
        self._show_plan_preview()

    def _setup_ui(self):
        self.setWindowTitle("Revert \u2014 Undo Current Plan")
        self.setMinimumSize(620, 400)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Revert Plan")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)

        # Plan preview
        self.preview_text = QtWidgets.QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(130)
        layout.addWidget(self.preview_text)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Result
        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(100)
        self.result_text.setVisible(False)
        layout.addWidget(self.result_text)

        layout.addStretch()

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_revert = QtWidgets.QPushButton("Execute Revert")
        self.btn_revert.setObjectName("accent-button")
        self.btn_revert.clicked.connect(self._on_revert)
        btn_row.addWidget(self.btn_revert)
        btn_row.addStretch()
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _show_plan_preview(self):
        actions = self.session.actions
        plan_file = self.session.plan_file
        if not actions:
            self.preview_text.setPlainText(
                "No plan loaded.\nPlease open or create a plan first."
            )
            self.btn_revert.setEnabled(False)
            return

        name = plan_file.name if plan_file else "(in memory)"
        lines = [
            f"Plan: {name}",
            f"Total actions: {len(actions)}",
            "",
            f"Will reverse {len(actions)} actions in reverse order.",
        ]
        if actions:
            lines.append("")
            lines.append("Last action to revert first:")
            lines.append(f"  {actions[-1].desc}")
            lines.append("First action to revert last:")
            lines.append(f"  {actions[0].desc}")

        self.preview_text.setPlainText("\n".join(lines))
        self.btn_revert.setEnabled(True)

    def _on_revert(self):
        actions = self.session.actions
        if not actions:
            QtWidgets.QMessageBox.warning(
                self, "No Plan", "No plan is currently loaded."
            )
            return

        self.btn_revert.setEnabled(False)
        self.result_text.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(actions))

        self._worker = PlanReverseWorker(actions, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)

    def _on_finished(self, success: int, errors: list):
        self.progress_bar.setVisible(False)
        total = len(self.session.actions)
        lines = [f"Revert complete: {success} of {total} succeeded"]
        if errors:
            lines.append(f"{len(errors)} failed:")
            for idx, desc, err in errors:
                lines.append(f"  - #{idx} {desc}: {err[:120]}")
        self.result_text.setPlainText("\n".join(lines))
        self.result_text.setVisible(True)
        self.btn_revert.setEnabled(True)
