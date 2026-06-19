# pages.py - 5 wizard pages for flchemist GUI
from __future__ import annotations
import json
from pathlib import Path
import logging
from PyQt6 import QtWidgets, QtCore, QtGui
from gui.models import DraftType, ActionStatus, ParamConfig, ExecuteResult, ExecuteDecision
from gui.workers import PlanWorker, ExecuteWorker
from gui.dialogs import ErrorChoiceDialog

from action import action_to_dict
from gui.tree_preview import TreePreviewWidget


class DraftSelectPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Draft 类型选招")
        self.setSubTitle('请选招觛行蟹的操作类型，或从已有的 .plan 文件导入')
        layout = QtWidgets.QVBoxLayout(self)
        self.radio_bt = {}
        for dt in DraftType:
            rb = QtWidgets.QRadioButton(dt.display_name())
            rb.setToolTip(dt.description())
            self.radio_bt[dt] = rb
            layout.addWidget(rb)
        layout.addStretch()
        self.radio_bt[DraftType.CLASSIFY_BY_TYPE].setChecked(True)
        self.registerField("draft_type", self, "draft_type_value")

    @QtCore.pyqtProperty(str)
    def draft_type_value(self):
        log = logging.getLogger("pages.DraftSelectPage")
        for dt, rb in self.radio_bt.items():
            if rb.isChecked():
                log.info("User selected draft type: %s", dt.value)
                return dt.value
        log.warning("No draft type selected")
        return ""

    def validatePage(self):
        for dt, rb in self.radio_bt.items():
            if rb.isChecked():
                return True
        QtWidgets.QMessageBox.warning(self, '提示', '请选招一个操作类型')
        return False
class ParamConfigPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle('参数配置')
        self.setSubTitle('请填写所我操的参数')
        main_layout = QtWidgets.QVBoxLayout(self)
        self.stack = QtWidgets.QStackedWidget()
        main_layout.addWidget(self.stack)

        tw = QtWidgets.QWidget()
        tl = QtWidgets.QFormLayout(tw)
        self.type_src, _ = self._make_path_input(tl, '源目录:', '选招源目录')
        self.type_dst, _ = self._make_path_input(tl, '目标目录:', '选招目标目录')
        self.type_extmap = QtWidgets.QPlainTextEdit()
        self.type_extmap.setPlaceholderText('可选，JSON格式自定义扩展对寿．如:{\\"images\\": [\\".jpg\\"]}')
        self.type_extmap.setMaximumHeight(100)
        tl.addRow('自定义 ext-map:', self.type_extmap)
        self.stack.addWidget(tw)

        dw = QtWidgets.QWidget()
        dl = QtWidgets.QFormLayout(dw)
        self.date_src, _ = self._make_path_input(dl, '源目录:', '选招源目录')
        self.date_dst, _ = self._make_path_input(dl, '目标目录:', '选招目标目录')
        self.date_pattern = QtWidgets.QLineEdit("%Y-%m")
        dl.addRow('日期格式:', self.date_pattern)
        self.date_usemtime = QtWidgets.QCheckBox('使用修改时间（取消则用创建时间）')
        self.date_usemtime.setChecked(True)
        dl.addRow(self.date_usemtime)
        self.stack.addWidget(dw)

        ww = QtWidgets.QWidget()
        wl = QtWidgets.QFormLayout(ww)
        self.wx_path, _ = self._make_path_input(wl, '微信数据目录:', '选招微信数据目录')
        self.wx_user = QtWidgets.QLineEdit()
        wl.addRow('用户 ID:', self.wx_user)
        self.wx_suffix = QtWidgets.QLineEdit()
        wl.addRow('后缀:', self.wx_suffix)
        self.wx_tar, _ = self._make_path_input(wl, '目标迁移目录:', '选招迁移目标目录')
        self.wx_endtime = QtWidgets.QLineEdit()
        self.wx_endtime.setPlaceholderText('默认当前月，格式 YYYY-MM')
        wl.addRow('截止时间:', self.wx_endtime)
        self.wx_nomove = QtWidgets.QCheckBox('不移动备份目录')
        wl.addRow(self.wx_nomove)
        self.stack.addWidget(ww)

    def _make_path_input(self, form, label, title):
        w = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        le = QtWidgets.QLineEdit()
        le.setPlaceholderText('点击右按选招目录')
        btn = QtWidgets.QPushButton("...")
        btn.setFixedWidth(30)
        btn.clicked.connect(lambda checked, e=le, t=title: self._browse_dir(e, t))
        hl.addWidget(le)
        hl.addWidget(btn)
        form.addRow(label, w)
        return le, btn

    def _browse_dir(self, le, title):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, title)
        if d:
            le.setText(d)

    def initializePage(self):
        dt_val = self.field("draft_type")
        dt = DraftType(dt_val) if dt_val else DraftType.CLASSIFY_BY_TYPE
        idx = {DraftType.CLASSIFY_BY_TYPE: 0, DraftType.CLASSIFY_BY_DATE: 1, DraftType.WECHAT_MIGRATE: 2}.get(dt, 0)
        self.stack.setCurrentIndex(idx)
        logging.getLogger("pages.ParamConfigPage").info("initializePage: field draft_type=%r, dt=%s", dt_val, dt)

    def validatePage(self):
        dt_val = self.field("draft_type")
        dt = DraftType(dt_val) if dt_val else None
        if dt == DraftType.CLASSIFY_BY_TYPE:
            if not self.type_src.text() or not self.type_dst.text():
                QtWidgets.QMessageBox.warning(self, '提示', '请填写源目录和目标目录')
                return False
        elif dt == DraftType.CLASSIFY_BY_DATE:
            if not self.date_src.text() or not self.date_dst.text():
                QtWidgets.QMessageBox.warning(self, '提示', '请填写源目录和目标目录')
                return False
        elif dt == DraftType.WECHAT_MIGRATE:
            if not self.wx_path.text() or not self.wx_user.text() or not self.wx_suffix.text() or not self.wx_tar.text():
                QtWidgets.QMessageBox.warning(self, '提示', '请填写所有必填字段')
                return False
        return True

    def get_config(self):
        from gui.models import ParamConfig
        config = ParamConfig()
        dt_val = self.field("draft_type")
        config.draft_type = DraftType(dt_val) if dt_val else None
        logging.getLogger("pages.ParamConfigPage").info("Building config for draft_type=%s, dt_val=%r", config.draft_type, dt_val)
        if config.draft_type == DraftType.CLASSIFY_BY_TYPE:
            config.src = Path(self.type_src.text())
            config.dst = Path(self.type_dst.text())
            ext_text = self.type_extmap.toPlainText().strip()
            if ext_text:
                try:
                    raw = json.loads(ext_text)
                    config.ext_map = {k: set(v) for k, v in raw.items()}
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "ext-map " + '格式错误', str(e))
                    return None
        elif config.draft_type == DraftType.CLASSIFY_BY_DATE:
            config.src = Path(self.date_src.text())
            config.dst = Path(self.date_dst.text())
            config.pattern = self.date_pattern.text() or "%Y-%m"
            config.use_mtime = self.date_usemtime.isChecked()
        elif config.draft_type == DraftType.WECHAT_MIGRATE:
            config.wx_path = Path(self.wx_path.text())
            config.user = self.wx_user.text()
            config.suffix = self.wx_suffix.text()
            config.tar_path = Path(self.wx_tar.text())
            config.end_time = self.wx_endtime.text() or ""
            config.no_move_backup = self.wx_nomove.isChecked()
        return config

class PlanPreviewPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("计划预览")
        self.setSubTitle("查看生成的操作列表和操作后文件结构预览")
        layout = QtWidgets.QVBoxLayout(self)
        self._actions = []
        self._plan_file = None
        
        self.status_label = QtWidgets.QLabel()
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "类型", "描述", "源路径录", "目标路径录"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(QtWidgets.QLabel("<b>Action 列表</b>"))
        layout.addWidget(self.table)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(self.table)
        
        self.tree_preview = TreePreviewWidget()
        splitter.addWidget(self.tree_preview)
        layout.addWidget(splitter)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_save = QtWidgets.QPushButton("保存为 .plan")
        btn_save.clicked.connect(self._save_plan)
        btn_layout.addWidget(btn_save)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _save_plan(self):
        if not self._plan_file:
            QtWidgets.QMessageBox.warning(self, "提示", "没有可保存的计划）")
            return
        import shutil
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存计划文件", str(self._plan_file), "Plan files (*.plan)")
        if path:
            shutil.copy2(str(self._plan_file), path)
            QtWidgets.QMessageBox.information(self, "成功", "计划已保存到: " + path)

    def set_generating(self):
        self.status_label.setText("Generating plan...")
        self.status_label.setVisible(True)
        self.table.setRowCount(0)
        self.tree_preview.clear()

    def set_actions(self, actions, plan_file):
        logging.getLogger("pages.PlanPreviewPage").info("Showing %d actions, plan_file=%s", len(actions), plan_file)
        self._actions = actions
        self._plan_file = plan_file
        self.status_label.setVisible(False)
        self.table.setRowCount(len(actions))
        for i, act in enumerate(actions):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(type(act).__name__))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(act.desc))
            self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(getattr(act, "src", ""))))
            self.table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(getattr(act, "dst", ""))))
        self.table.resizeColumnsToContents()
        self.tree_preview.set_actions(actions)
        self.completeChanged.emit()

    def get_plan_info(self):
        return self._actions, self._plan_file

    def isComplete(self):
        actions_ready = len(self._actions) > 0
        if not actions_ready:
            self.status_label.setText("Generating plan...")
            self.status_label.setVisible(True)
        return actions_ready

class ExecutePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("执行进度")
        self.setSubTitle("正在执行操作……")
        layout = QtWidgets.QVBoxLayout(self)
        self.progress_bar = QtWidgets.QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_table = QtWidgets.QTableWidget(0, 6)
        h = ["#", "类型", "描述", "源路径录", "目标路径录", "状态"]
        self.status_table.setHorizontalHeaderLabels(h)
        self.status_table.horizontalHeader().setStretchLastSection(True)
        self.status_table.setAlternatingRowColors(True)
        layout.addWidget(self.status_table)
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_abort = QtWidgets.QPushButton("中止")
        self.btn_abort.clicked.connect(self._abort)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_abort)
        layout.addLayout(btn_layout)
        self._actions = []
        self._worker = None
        self._result = None

    def initializePage(self):
        wiz = self.wizard()
        self._actions = getattr(wiz, "_actions", [])
        plan_file = getattr(wiz, "_plan_file", None)
        self.status_table.setRowCount(len(self._actions))
        for i, act in enumerate(self._actions):
            self.status_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i + 1)))
            self.status_table.setItem(i, 1, QtWidgets.QTableWidgetItem(type(act).__name__))
            self.status_table.setItem(i, 2, QtWidgets.QTableWidgetItem(act.desc))
            self.status_table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(getattr(act, "src", ""))))
            self.status_table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(getattr(act, "dst", ""))))
            item = QtWidgets.QTableWidgetItem(ActionStatus.PENDING.display_char())
            self.status_table.setItem(i, 5, item)
        self.status_table.resizeColumnsToContents()
        self.progress_bar.setRange(0, len(self._actions))
        self.progress_bar.setValue(0)
        self.btn_abort.setEnabled(True)
        from datetime import datetime
        from pathlib import Path
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{ts}_exec.jsonl"
        self._worker = ExecuteWorker(self._actions, log_file, plan_file, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.action_status.connect(self._on_action_status)
        self._worker.action_failed_request.connect(self._on_action_failed)
        self._worker.finished.connect(self._on_finished)
        logging.getLogger("pages.ExecutePage").info("Starting execution of %d actions", len(self._actions))
        self._worker.start()

    def _on_progress(self, idx):
        self.progress_bar.setValue(idx)

    def _on_action_status(self, idx, status_str):
        from gui.models import ActionStatus as AS
        status = AS(status_str)
        item = self.status_table.item(idx - 1, 5)
        if item:
            item.setText(status.display_char())
            from PyQt6 import QtGui
            if status == AS.SUCCESS:
                item.setBackground(QtGui.QColor("#e8f5e9"))
            elif status == AS.FAILED:
                item.setBackground(QtGui.QColor("#ffebee"))

    def _on_action_failed(self, idx, desc, error):
        log = logging.getLogger("pages.ExecutePage")
        log.warning("Action %d failed: %s - %s", idx, desc, error)
        dlg = ErrorChoiceDialog(idx, desc, error, self)
        # Store decision locally first (main thread), then wake worker
        dlg.decision_made.connect(lambda dec: self._worker.set_user_decision(dec))
        dlg.exec()

    def _on_finished(self, result):
        log = logging.getLogger("pages.ExecutePage")
        log.info("Execution finished: %d success, %d failed, decision=%s", result.success, result.failed, result.decision)
        self._result = result
        self.progress_bar.setValue(result.total)
        self.btn_abort.setEnabled(False)
        wiz = self.wizard()
        wiz._execute_result = result
        wiz._log_file = result.log_file
        self.completeChanged.emit()

    def _abort(self):
        logging.getLogger("pages.ExecutePage").info("User clicked abort")
        if self._worker:
            self._worker.cancel()

    def isComplete(self):
        return self._result is not None

class FinishPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("执行完成")
        self.setSubTitle("操作执行结果总结")
        layout = QtWidgets.QVBoxLayout(self)
        self.summary = QtWidgets.QTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_view = QtWidgets.QPushButton("查看计划文件")
        btn_view.clicked.connect(self._view_plan)
        btn_restart = QtWidgets.QPushButton("重新始妯")
        btn_restart.clicked.connect(self._restart)
        btn_exit = QtWidgets.QPushButton("退出")
        btn_exit.clicked.connect(QtWidgets.QApplication.instance().quit)
        btn_layout.addWidget(btn_view)
        btn_layout.addWidget(btn_restart)
        btn_layout.addWidget(btn_exit)
        layout.addLayout(btn_layout)

    def initializePage(self):
        wiz = self.wizard()
        result = getattr(wiz, "_execute_result", None)
        if not result:
            self.summary.setPlainText("无执行结果")
            return
        from gui.models import ExecuteDecision
        import datetime
        lines = []
        lines.append(f"总操作数: {result.total}")
        lines.append(f"成功: {result.success}")
        lines.append(f"失败: {result.failed}")
        if result.decision:
            d = "中止当前操作" if result.decision == ExecuteDecision.ABORT else "全部回滚"
            lines.append(f"用户决策: {d}")
        if result.reverse_errors:
            lines.append("")
            lines.append("回滚错误:")
            for err in result.reverse_errors:
                lines.append(f"  - {err}")
        if result.log_file:
            lines.append("")
            lines.append(f"日志文件: {result.log_file}")
        if result.plan_file:
            lines.append(f"计划文件: {result.plan_file}")
        self.summary.setPlainText(chr(10).join(lines))

    def _view_plan(self):
        wiz = self.wizard()
        plan_file = getattr(wiz, "_plan_file", None)
        if plan_file and plan_file.exists():
            from PyQt6 import QtGui, QtCore
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(plan_file)))

    def _restart(self):
        self.wizard().restart()
