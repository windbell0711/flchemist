from __future__ import annotations
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6 import QtWidgets, QtCore

from gui.models import DraftType, ParamConfig
from gui.session import Session
from gui.workers import PlanWorker


class DraftDialog(QtWidgets.QDialog):
    """Configure draft type + parameters, generate plan, save to file."""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._actions: list = []
        self._plan_file: Optional[Path] = None
        self._log = logging.getLogger("flchemist.DraftDialog")
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setWindowTitle("Draft \u2014 Create a Plan")
        self.setMinimumSize(640, 520)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Create a New Plan")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel(
            "Select the operation type and configure parameters."
        )
        subtitle.setStyleSheet("font-size: 11px; color: #888888; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # --- Type Selection ---
        type_group = QtWidgets.QGroupBox("Operation Type")
        type_layout = QtWidgets.QVBoxLayout(type_group)
        self.radio_btns: dict[DraftType, QtWidgets.QRadioButton] = {}
        for dt in DraftType:
            if dt == DraftType.FROM_PLAN_FILE:
                continue
            rb = QtWidgets.QRadioButton(dt.display_name())
            rb.setToolTip(dt.description())
            self.radio_btns[dt] = rb
            type_layout.addWidget(rb)
        self.radio_btns[DraftType.CLASSIFY_BY_TYPE].setChecked(True)
        layout.addWidget(type_group)

        # --- Param Form (stacked) ---
        self.param_stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.param_stack)
        self._build_type_page()
        self._build_date_page()
        self._build_wechat_page()
        self._on_type_changed(DraftType.CLASSIFY_BY_TYPE)

        # --- Status ---
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; color: #888888;")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # --- Action buttons ---
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.btn_generate = QtWidgets.QPushButton("Generate Plan")
        self.btn_generate.setObjectName("accent-button")
        btn_row.addWidget(self.btn_generate)
        layout.addLayout(btn_row)

        self.btn_close = QtWidgets.QPushButton("Close")
        close_row = QtWidgets.QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(self.btn_close)
        layout.addLayout(close_row)

    def _build_type_page(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        form.setSpacing(8)
        self.type_src, _ = self._make_path_input(
            form, "Source Directory:", "Select source directory"
        )
        self.type_dst, _ = self._make_path_input(
            form, "Target Directory:", "Select target directory"
        )
        self.type_extmap = QtWidgets.QPlainTextEdit()
        self.type_extmap.setPlaceholderText(
            'Optional JSON, e.g. {"images": [".jpg", ".png"]}'
        )
        self.type_extmap.setMaximumHeight(80)
        form.addRow("Custom ext-map:", self.type_extmap)
        self.param_stack.addWidget(w)

    def _build_date_page(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        form.setSpacing(8)
        self.date_src, _ = self._make_path_input(
            form, "Source Directory:", "Select source directory"
        )
        self.date_dst, _ = self._make_path_input(
            form, "Target Directory:", "Select target directory"
        )
        self.date_pattern = QtWidgets.QLineEdit("%Y-%m")
        form.addRow("Date pattern:", self.date_pattern)
        self.date_usemtime = QtWidgets.QCheckBox(
            "Use modification time (uncheck = creation time)"
        )
        self.date_usemtime.setChecked(True)
        form.addRow(self.date_usemtime)
        self.param_stack.addWidget(w)

    def _build_wechat_page(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        form.setSpacing(8)
        self.wx_path, _ = self._make_path_input(
            form, "WeChat Data Directory:", "Select WeChat data directory"
        )
        self.wx_user = QtWidgets.QLineEdit()
        form.addRow("User ID:", self.wx_user)
        self.wx_suffix = QtWidgets.QLineEdit()
        form.addRow("Suffix:", self.wx_suffix)
        self.wx_tar, _ = self._make_path_input(
            form, "Target Migration Directory:", "Select migration target"
        )
        self.wx_endtime = QtWidgets.QLineEdit()
        self.wx_endtime.setPlaceholderText(
            "Default: current month, format YYYY-MM"
        )
        form.addRow("Cutoff time:", self.wx_endtime)
        self.wx_nomove = QtWidgets.QCheckBox("Do not move backup directory")
        form.addRow(self.wx_nomove)
        self.param_stack.addWidget(w)

    # ---------- helpers ----------

    def _make_path_input(self, form, label, title):
        container = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(container)
        hl.setContentsMargins(0, 0, 0, 0)
        le = QtWidgets.QLineEdit()
        le.setPlaceholderText("Click [...] to browse")
        btn = QtWidgets.QPushButton("...")
        btn.setFixedWidth(30)
        btn.clicked.connect(
            lambda checked, e=le, t=title: self._browse_dir(e, t)
        )
        hl.addWidget(le)
        hl.addWidget(btn)
        form.addRow(label, container)
        return le, btn

    @staticmethod
    def _browse_dir(le: QtWidgets.QLineEdit, title: str):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            le.parent().window() if le.parent() else None, title
        )
        if d:
            le.setText(d)

    def _connect_signals(self):
        for dt, rb in self.radio_btns.items():
            rb.toggled.connect(
                lambda checked, d=dt: self._on_type_changed(d) if checked else None
            )
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_close.clicked.connect(self.reject)

    def _on_type_changed(self, dt: DraftType):
        idx = {
            DraftType.CLASSIFY_BY_TYPE: 0,
            DraftType.CLASSIFY_BY_DATE: 1,
            DraftType.WECHAT_MIGRATE: 2,
        }.get(dt, 0)
        self.param_stack.setCurrentIndex(idx)

    def _selected_type(self) -> Optional[DraftType]:
        for dt, rb in self.radio_btns.items():
            if rb.isChecked():
                return dt
        return None

    def _build_config(self) -> Optional[ParamConfig]:
        dt = self._selected_type()
        if dt is None:
            return None
        config = ParamConfig()
        config.draft_type = dt
        try:
            if dt == DraftType.CLASSIFY_BY_TYPE:
                src = self.type_src.text().strip()
                dst = self.type_dst.text().strip()
                if not src or not dst:
                    raise ValueError("Source and Target directories are required")
                config.src = Path(src)
                config.dst = Path(dst)
                ext_text = self.type_extmap.toPlainText().strip()
                if ext_text:
                    config.ext_map = json.loads(ext_text)
            elif dt == DraftType.CLASSIFY_BY_DATE:
                src = self.date_src.text().strip()
                dst = self.date_dst.text().strip()
                if not src or not dst:
                    raise ValueError("Source and Target directories are required")
                config.src = Path(src)
                config.dst = Path(dst)
                config.pattern = self.date_pattern.text().strip() or "%Y-%m"
                config.use_mtime = self.date_usemtime.isChecked()
            elif dt == DraftType.WECHAT_MIGRATE:
                wx_path = self.wx_path.text().strip()
                user = self.wx_user.text().strip()
                suffix = self.wx_suffix.text().strip()
                tar = self.wx_tar.text().strip()
                if not wx_path or not user or not suffix or not tar:
                    raise ValueError("All WeChat migration fields are required")
                config.wx_path = Path(wx_path)
                config.user = user
                config.suffix = suffix
                config.tar_path = Path(tar)
                config.end_time = self.wx_endtime.text().strip()
                config.no_move_backup = self.wx_nomove.isChecked()
        except (ValueError, json.JSONDecodeError) as e:
            QtWidgets.QMessageBox.warning(
                self, "Invalid Parameters", str(e)
            )
            return None
        return config

    # ---------- generate ----------

    def _on_generate(self):
        config = self._build_config()
        if config is None:
            return

        suggested = (
            f"plan_{config.draft_type.value}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.plan"
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Plan As", suggested, "Plan files (*.plan)"
        )
        if not path:
            return

        self._plan_file = Path(path)

        self.status_label.setText("Generating plan...")
        self.status_label.setVisible(True)
        self.btn_generate.setEnabled(False)

        self._worker = PlanWorker(config, self)
        self._worker.plan_ready.connect(self._on_plan_ready)
        self._worker.plan_error.connect(self._on_plan_error)
        self._worker.start()

    def _on_plan_ready(self, actions, auto_plan_file):
        self._actions = actions

        if self._plan_file and auto_plan_file != self._plan_file:
            self._plan_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(auto_plan_file), str(self._plan_file))

        self.session.actions = actions
        self.session.plan_file = self._plan_file or auto_plan_file

        self.status_label.setText(
            f"Plan generated: {len(actions)} actions  |  Saved: {self.session.plan_file.name}"
        )
        self.btn_generate.setVisible(False)

    def _on_plan_error(self, error):
        self.status_label.setText("Generation failed")
        self.btn_generate.setEnabled(True)
        QtWidgets.QMessageBox.critical(self, "Plan Generation Failed", error)
