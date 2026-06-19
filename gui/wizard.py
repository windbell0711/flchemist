# wizard.py - Main QWizard for flchemist
from __future__ import annotations
from PyQt6 import QtWidgets, QtCore, QtGui
import logging
from gui.pages import DraftSelectPage, ParamConfigPage, PlanPreviewPage, ExecutePage, FinishPage
from gui.models import DraftType
from gui.workers import PlanWorker

class FlchemistWizard(QtWidgets.QWizard):
    _log = logging.getLogger("flchemist.Wizard")
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("flchemist - Windows 文件批量处理工具")
        self.setMinimumSize(900, 650)
        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        self._actions = []
        self._plan_file = None
        self._execute_result = None
        self._log_file = None

        # Add pages
        self.draft_select_page = DraftSelectPage()
        self.param_config_page = ParamConfigPage()
        self.plan_preview_page = PlanPreviewPage()
        self.execute_page = ExecutePage()
        self.finish_page = FinishPage()

        self.addPage(self.draft_select_page)
        self.addPage(self.param_config_page)
        self.addPage(self.plan_preview_page)
        self.addPage(self.execute_page)
        self.addPage(self.finish_page)
        
        # Connect AFTER all pages are added
        self.currentIdChanged.connect(self._on_page_changed)

    def _on_page_changed(self, page_id):
        self._log.info("Page changed to %d", page_id)
        if page_id < 0 or page_id > 4:
            self._log.warning("Unexpected page_id: %d", page_id)
            return
        if page_id == 2:  # PlanPreviewPage
            self._log.info("Triggering plan generation...")
            self._generate_plan()
            self._log.info("Plan generation initiated")

    def _generate_plan(self):
        """Generate actions from config or import from plan file"""
        dt_val = self.field("draft_type")
        dt = DraftType(dt_val) if dt_val else None

        if dt == DraftType.FROM_PLAN_FILE:
            self._log.info("User chose to import from .plan file")
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选招入.plan文件", "", "Plan files (*.plan)")
            if not path:
                self.restart()
                return
            import json
            from action import action_from_dict
            with open(path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
            self._actions = [action_from_dict(a) for a in plan_data.get("actions", [])]
            self._plan_file = path
            self._log.info("Imported %d actions from %s", len(self._actions), path)
            self.plan_preview_page.set_actions(self._actions, path)
        else:
            config = self.param_config_page.get_config()
            if config is None:
                self._log.warning("Config is None, restarting")
                self.restart()
                return
            self._log.info("Generating plan for %s", config.draft_type)
            self.plan_preview_page.set_generating()
            self._worker = PlanWorker(config, self)
            self._worker.plan_ready.connect(self._on_plan_ready)
            self._worker.plan_error.connect(self._on_plan_error)
            self._worker.start()

    def _on_plan_ready(self, actions, plan_file):
        self._log.info("Plan ready: %d actions, file=%s", len(actions), plan_file)
        self._actions = actions
        self._plan_file = plan_file
        self.plan_preview_page.set_actions(actions, plan_file)

    def _on_plan_error(self, error):
        self._log.error("Plan error: %s", error)
        QtWidgets.QMessageBox.critical(self, "生成计划失败", error)
        self.restart()
