from __future__ import annotations
from PyQt6 import QtWidgets


class InfoDialog(QtWidgets.QDialog):
    """Explains the plan mechanism and usage workflow."""

    def __init__(self, parent=None):
        super().__init__(parent)
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
        text.setHtml("""
        <p>flchemist uses a <b>plan-based workflow</b> to batch-process files safely.</p>

        <h3 style="color:#0078d4;">1. Draft</h3>
        <p>Choose an operation type and configure parameters. A <b>.plan file</b> is generated,
        containing a list of reversible actions (Copy, Move, Rename, Junction).</p>

        <h3 style="color:#0078d4;">2. Open</h3>
        <p>Load an existing .plan file into the main window. The right panel shows a
        <b>tree preview</b> of file changes and a full action list.</p>

        <h3 style="color:#0078d4;">3. Execute</h3>
        <p>Run each action in sequence. On failure you can:<br>
        &nbsp;&bull; <b>Abort</b> \u2014 roll back the failed action only and stop<br>
        &nbsp;&bull; <b>Rollback All</b> \u2014 undo every completed action and stop</p>

        <h3 style="color:#0078d4;">4. Revert</h3>
        <p>Reverse the currently loaded plan. Actions are undone in reverse order,
        restoring the original state.</p>

        <h3 style="color:#0078d4;">Logs</h3>
        <p>Execution logs are saved to <tt>logs/</tt> for auditing, but are not used for revert.</p>

        <hr style="border-color:#3c3c3c;">
        <p style="color:#888888; font-size:11px;">
        Each action has a built-in <tt>reverse()</tt> method, so the tool always knows
        how to undo what it did.
        </p>
        """)
        layout.addWidget(text)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
