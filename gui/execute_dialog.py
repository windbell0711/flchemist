from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path

from PyQt6 import QtWidgets, QtCore, QtGui

from gui.models import ActionStatus as AS, ExecuteResult, ExecuteDecision
from gui.session import Session
from gui.workers import ExecuteWorker
from gui.dialogs import ErrorChoiceDialog


class ExecuteDialog(QtWidgets.QDialog):
    """Run the plan with progress, status table, and failure handling."""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._worker: ExecuteWorker | None = None
        self._result: ExecuteResult | None = None
        self._log = logging.getLogger("flchemist.ExecuteDialog")
        self._setup_ui()
        QtCore.QTimer.singleShot(100, self._start_execution)

    def _setup_ui(self):
        self.setWindowTitle("Execute \u2014 Run Plan")
        self.setMinimumSize(800, 550)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Executing Plan")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)

        self.status_label = QtWidgets.QLabel("Initializing...")
        self.status_label.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(self.status_label)

        # Progress
        progress_row = QtWidgets.QHBoxLayout()
        progress_row.addWidget(QtWidgets.QLabel("Progress:"))
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximum(100)
        progress_row.addWidget(self.progress_bar)
        self.progress_text = QtWidgets.QLabel("0 / 0")
        self.progress_text.setMinimumWidth(80)
        progress_row.addWidget(self.progress_text)
        layout.addLayout(progress_row)

        # Status table
        self.status_table = QtWidgets.QTableWidget()
        self.status_table.setColumnCount(4)
        self.status_table.setHorizontalHeaderLabels(["#", "Type", "Description", "Status"])
        self.status_table.horizontalHeader().setStretchLastSection(True)
        self.status_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.status_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.status_table.verticalHeader().setVisible(False)

        actions = self.session.actions
        self.status_table.setRowCount(len(actions))
        for i, act in enumerate(actions):
            self.status_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i + 1)))
            self.status_table.setItem(i, 1, QtWidgets.QTableWidgetItem(type(act).__name__))
            self.status_table.setItem(i, 2, QtWidgets.QTableWidgetItem(act.desc))
            self.status_table.setItem(i, 3, QtWidgets.QTableWidgetItem("\u23f3"))
        self.status_table.resizeColumnsToContents()
        layout.addWidget(self.status_table)

        # Summary (hidden until completion)
        self.summary_group = QtWidgets.QGroupBox("Execution Summary")
        self.summary_group.setVisible(False)
        summary_layout = QtWidgets.QVBoxLayout(self.summary_group)
        self.summary_text = QtWidgets.QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(120)
        summary_layout.addWidget(self.summary_text)
        layout.addWidget(self.summary_group)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        self.btn_abort = QtWidgets.QPushButton("Abort")
        self.btn_abort.setEnabled(False)
        self.btn_abort.clicked.connect(self._abort)
        btn_row.addWidget(self.btn_abort)
        btn_row.addStretch()
        self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

    def _start_execution(self):
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{ts}_exec.jsonl"

        self._worker = ExecuteWorker(
            self.session.actions, log_file, self.session.plan_file, self
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.action_status.connect(self._on_action_status)
        self._worker.action_failed_request.connect(self._on_action_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
        self.status_label.setText("Running...")
        self.btn_abort.setEnabled(True)

    def _on_progress(self, idx: int):
        total = len(self.session.actions)
        pct = int(idx / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.progress_text.setText(f"{idx} / {total}")

    def _on_action_status(self, idx: int, status_str: str):
        status = AS(status_str)
        item = self.status_table.item(idx - 1, 3)
        if item:
            item.setText(status.display_char())
            if status == AS.SUCCESS:
                item.setBackground(QtGui.QColor("#1a3a2a"))
            elif status == AS.FAILED:
                item.setBackground(QtGui.QColor("#3a1a1a"))
            elif status == AS.RUNNING:
                item.setBackground(QtGui.QColor("#1a2a3a"))

    def _on_action_failed(self, idx: int, desc: str, error: str):
        dlg = ErrorChoiceDialog(idx, desc, error, self)
        dlg.decision_made.connect(
            lambda dec: self._worker.set_user_decision(dec)
        )
        dlg.exec()

    def _on_finished(self, result: ExecuteResult):
        self._result = result
        self.session.result = result
        self.session.log_file = result.log_file

        total = result.total
        self.progress_bar.setValue(100 if total > 0 else 0)
        self.progress_text.setText(f"{total} / {total}")
        self.btn_abort.setEnabled(False)

        lines = [
            f"Total actions: {total}",
            f"Success: {result.success}",
            f"Failed: {result.failed}",
        ]
        if result.decision:
            d = "Abort current" if result.decision == ExecuteDecision.ABORT else "Rollback all"
            lines.append(f"User decision: {d}")
        if result.reverse_errors:
            lines.append("")
            lines.append("Rollback errors:")
            for err in result.reverse_errors:
                lines.append(f"  - {err}")
        self.summary_text.setPlainText("\n".join(lines))
        self.summary_group.setVisible(True)
        self.status_label.setText("Execution complete")

    def _abort(self):
        if self._worker:
            self._worker.cancel()
            self.status_label.setText("Aborting...")
