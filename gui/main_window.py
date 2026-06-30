from __future__ import annotations
import json
import logging
from pathlib import Path

from PyQt6 import QtWidgets, QtCore, QtGui

from gui.session import Session
from gui.draft_dialog import DraftDialog
from gui.execute_dialog import ExecuteDialog
from gui.revert_dialog import RevertDialog
from gui.info_dialog import InfoDialog

from action import action_from_dict


class MainWindow(QtWidgets.QMainWindow):
    """Minimal dark-themed main window with left sidebar + right plan preview."""

    def __init__(self):
        super().__init__()
        self._log = logging.getLogger("flchemist.MainWindow")
        self.session = Session()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("flchemist")
        self.setMinimumSize(960, 600)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==================== Left sidebar ====================
        left_widget = QtWidgets.QWidget()
        left_widget.setObjectName("sidebar")
        left_widget.setFixedWidth(260)
        left_widget.setStyleSheet(
            "QWidget#sidebar { background-color: #252525; border-right: 1px solid #3c3c3c; }"
        )
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 24, 16, 16)
        left_layout.setSpacing(8)
        left_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        # Title
        title = QtWidgets.QLabel("flchemist")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #0078d4; "
            "background: transparent; margin-bottom: 24px;"
        )
        left_layout.addWidget(title)

        # Phase buttons
        self.btn_draft = self._make_side_button("\U0001f4dd  Draft", "Create a new plan")
        self.btn_draft.clicked.connect(self._open_draft)
        left_layout.addWidget(self.btn_draft)

        self.btn_open = self._make_side_button("\U0001f4c2  Open", "Open an existing plan file")
        self.btn_open.clicked.connect(self._open_plan)
        left_layout.addWidget(self.btn_open)

        self.btn_execute = self._make_side_button("\u25b6  Execute", "Run the plan")
        self.btn_execute.clicked.connect(self._open_execute)
        self.btn_execute.setEnabled(False)
        left_layout.addWidget(self.btn_execute)

        self.btn_revert = self._make_side_button("\u21a9  Revert", "Undo the current plan")
        self.btn_revert.clicked.connect(self._open_revert)
        self.btn_revert.setEnabled(False)
        left_layout.addWidget(self.btn_revert)

        self.btn_info = self._make_side_button("ℹ️  Info", "Learn how flchemist works")
        self.btn_info.clicked.connect(self._open_info)
        left_layout.addWidget(self.btn_info)

        left_layout.addStretch()

        # Status
        self.status_label = QtWidgets.QLabel("No plan loaded")
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size: 11px; color: #666666; background: transparent;"
        )
        left_layout.addWidget(self.status_label)

        # ==================== Right panel ====================
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(8)

        # Plan header
        self.plan_header = QtWidgets.QLabel("Welcome to flchemist")
        self.plan_header.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #e0e0e0; background: transparent;"
        )
        right_layout.addWidget(self.plan_header)

        self.plan_info = QtWidgets.QLabel(
            "Create or open a plan to get started."
        )
        self.plan_info.setStyleSheet(
            "font-size: 11px; color: #888888; margin-bottom: 4px; background: transparent;"
        )
        right_layout.addWidget(self.plan_info)

        # Placeholder shown when no plan is loaded
        self.empty_label = QtWidgets.QLabel()
        self.empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            "font-size: 13px; color: #555555; background: transparent;"
        )
        right_layout.addWidget(self.empty_label)

        # Tree + table splitter (hidden until plan loaded)
        self.plan_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.plan_splitter.setVisible(False)




        self.action_table = QtWidgets.QTableWidget()
        self.action_table.setColumnCount(3)
        self.action_table.setHorizontalHeaderLabels(["#", "Type", "Description"])
        self.action_table.horizontalHeader().setStretchLastSection(True)
        self.action_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.action_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.action_table.verticalHeader().setVisible(False)
        self.plan_splitter.addWidget(self.action_table)

        right_layout.addWidget(self.plan_splitter)

        # ==================== Assemble ====================
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setHandleWidth(0)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def _make_side_button(self, text: str, tooltip: str) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName("phase-button")
        btn.setToolTip(tooltip)
        btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(48)
        btn.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: bold; padding: 12px 16px; "
            "border-radius: 8px; text-align: left; }"
        )
        return btn

    # ==================== Display helpers ====================

    def _show_empty_state(self, message: str = ""):
        self.plan_splitter.setVisible(False)
        self.empty_label.setVisible(True)
        self.empty_label.setText(message or "Create or open\na plan to get started.")
        self.plan_header.setText("No plan loaded")
        self.plan_info.setText("")

    def _show_plan(self):
        if not self.session.actions:
            self._show_empty_state()
            return

        self.plan_splitter.setVisible(True)
        self.empty_label.setVisible(False)

        name = self.session.plan_file.name if self.session.plan_file else "(in memory)"
        self.plan_header.setText(f"Plan: {name}")
        self.plan_info.setText(f"{len(self.session.actions)} actions")

        # Tree preview


        # Action table
        actions = self.session.actions
        self.action_table.setRowCount(len(actions))
        for i, act in enumerate(actions):
            self.action_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i + 1)))
            self.action_table.setItem(i, 1, QtWidgets.QTableWidgetItem(type(act).__name__))
            self.action_table.setItem(i, 2, QtWidgets.QTableWidgetItem(act.desc))
        self.action_table.resizeColumnsToContents()

    def _update_session_state(self):
        has_plan = len(self.session.actions) > 0
        self.btn_execute.setEnabled(has_plan)
        self.btn_revert.setEnabled(has_plan)
        if has_plan:
            self._show_plan()
        else:
            self._show_empty_state()
        if self.session.plan_file:
            self.status_label.setText(f"{self.session.plan_file.name}")
        else:
            self.status_label.setText("No plan loaded")

    # ==================== Actions ====================

    def _open_draft(self):
        dlg = DraftDialog(self.session, self)
        result = dlg.exec()
        self._update_session_state()

    def _open_plan(self):
        default_dir = ""
        plans_path = Path("plans")
        if plans_path.is_dir():
            default_dir = str(plans_path.resolve())
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Plan", default_dir, "Plan files (*.plan)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
            self.session.actions = [
                action_from_dict(a) for a in plan_data.get("actions", [])
            ]
            self.session.plan_file = Path(path)
            self._log.info(
                "Opened plan: %s (%d actions)", path, len(self.session.actions)
            )
            self._update_session_state()
        except Exception as e:
            self._log.error("Failed to open plan: %s", e)
            QtWidgets.QMessageBox.critical(self, "Open Failed", str(e))

    def _open_execute(self):
        if not self.session.actions:
            return
        dlg = ExecuteDialog(self.session, self)
        dlg.exec()
        self._update_session_state()

    def _open_info(self):
        dlg = InfoDialog(self)
        dlg.exec()

    def _open_revert(self):
        if not self.session.actions:
            return
        dlg = RevertDialog(self.session, self)
        dlg.exec()
