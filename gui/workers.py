from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6 import QtCore

_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from action import Action, action_to_dict, action_from_dict
from drafts import draft_classify_by_type, draft_classify_by_date, draft_wechat_junction
import logging
from gui.models import DraftType, ParamConfig, ExecuteResult, ExecuteDecision
from main import _log_write

_LOG_DIR = Path(_parent) / 'logs'


class PlanWorker(QtCore.QThread):
    _log = logging.getLogger('flchemist.PlanWorker')
    plan_ready = QtCore.pyqtSignal(list, object)
    plan_error = QtCore.pyqtSignal(str)

    def __init__(self, config: ParamConfig, parent=None):
        super().__init__(parent)
        self._config = config

    def run(self):
        try:
            config = self._config
            if config.draft_type == DraftType.FROM_PLAN_FILE:
                with open(config.plan_file, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                actions = [action_from_dict(a) for a in plan_data['actions']]
                plan_file = config.plan_file
            else:
                actions = self._build_actions(config)
                plan_file = self._save_plan(actions, config)
            self._log.info('Plan generated: %d actions, saved to %s', len(actions), plan_file)
            self.plan_ready.emit(actions, plan_file)
        except Exception as e:
            self._log.error('Plan generation failed: %s', str(e))
            tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            self.plan_error.emit(str(e) + '\n' + tb)

    def _build_actions(self, config: ParamConfig) -> list[Action]:
        dt = config.draft_type
        if dt == DraftType.CLASSIFY_BY_TYPE:
            return draft_classify_by_type(config.src, config.dst, extensions_map=config.ext_map)
        elif dt == DraftType.CLASSIFY_BY_DATE:
            return draft_classify_by_date(config.src, config.dst, pattern=config.pattern, use_mtime=config.use_mtime)
        elif dt == DraftType.WECHAT_MIGRATE:
            return draft_wechat_junction(config.wx_path, config.user, config.suffix, config.tar_path, config.end_time, move_backup=not config.no_move_backup)
        self._log.warning('Unknown draft type: %s', dt)
        raise ValueError(f'Unknown draft type: {dt}')

    def _save_plan(self, actions, config):
        plans_dir = Path(_parent) / 'plans'
        plans_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        name = config.draft_type.value if config.draft_type else 'unknown'
        plan_file = plans_dir / f'{ts}_{name}.plan'
        plan_data = {'draft': name, 'created_at': datetime.now().isoformat(), 'actions': [action_to_dict(a) for a in actions]}
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)
        return plan_file


class ExecuteWorker(QtCore.QThread):
    _log = logging.getLogger('flchemist.ExecuteWorker')
    progress = QtCore.pyqtSignal(int)
    action_status = QtCore.pyqtSignal(int, str)
    action_failed_request = QtCore.pyqtSignal(int, str, str)
    finished = QtCore.pyqtSignal(object)

    def __init__(self, actions, log_file, plan_file, parent=None):
        super().__init__(parent)
        self._actions = actions
        self._log_file = log_file
        self._plan_file = plan_file
        self._canceled = False
        self._ignore_all = False
        self._user_decision = None
        self._mutex = QtCore.QMutex()
        self._wait_cond = QtCore.QWaitCondition()

    def cancel(self):
        self._canceled = True

    def set_user_decision(self, decision):
        self._mutex.lock()
        self._user_decision = decision
        self._mutex.unlock()
        self._wait_cond.wakeAll()

    def run(self):
        result = ExecuteResult()
        result.total = len(self._actions)
        result.plan_file = self._plan_file
        result.log_file = self._log_file

        _LOG_DIR.mkdir(exist_ok=True)
        _log_write(self._log_file, {'event': 'start', 'total': result.total})

        completed = []
        for i, act in enumerate(self._actions, 1):
            if self._canceled:
                self.progress.emit(i - 1)
                break

            self.progress.emit(i)
            self.action_status.emit(i, 'running')

            try:
                act.run()
                completed.append((i, act))
                result.success += 1
                self.action_status.emit(i, 'success')
                _log_write(self._log_file, {'event': 'action_done', 'index': i, 'desc': act.desc, 'status': 'done', 'action_data': action_to_dict(act)})
            except Exception as e:
                result.failed += 1
                self.action_status.emit(i, 'failed')
                tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                _log_write(self._log_file, {'event': 'action_failed', 'index': i, 'desc': act.desc, 'status': 'failed', 'error': tb_str})

                if self._ignore_all:
                    decision = 'ignore'
                else:
                    self._user_decision = None
                    self.action_failed_request.emit(i, act.desc, str(e))

                    self._mutex.lock()
                    while self._user_decision is None and not self._canceled:
                        self._wait_cond.wait(self._mutex)
                    self._mutex.unlock()

                    decision = self._user_decision
                    if decision == 'ignore_all':
                        self._ignore_all = True
                        decision = 'ignore'

                result.decision = ExecuteDecision(decision)
                self._log.info('User decision: %s for action %d (%s)', decision, i, act.desc)
                _log_write(self._log_file, {'event': 'user_decision', 'index': i, 'decision': decision, 'desc': act.desc})

                if decision == 'abort':
                    self._log.info('Rolling back single action %d: %s', i, act.desc)
                    try:
                        act.reverse()
                        self._log.info('Rollback OK: action %d', i)
                        _log_write(self._log_file, {'event': 'reverse_single', 'index': i, 'desc': act.desc, 'status': 'done'})
                    except Exception as rev_e:
                        rev_tb = ''.join(traceback.format_exception(type(rev_e), rev_e, rev_e.__traceback__))
                        result.reverse_errors.append(f'[rollback single] #{i} {act.desc}: {rev_e}')
                        self._log.error('Rollback failed for action %d: %s', i, str(rev_e))
                        _log_write(self._log_file, {'event': 'reverse_single', 'index': i, 'desc': act.desc, 'status': 'failed', 'error': rev_tb})
                    break
                elif decision == 'rollback_all':
                    self._log.info('Rolling back ALL %d completed actions', len(completed))
                    for rev_idx, rev_act in reversed(completed):
                        try:
                            rev_act.reverse()
                            _log_write(self._log_file, {'event': 'reverse_all', 'index': rev_idx, 'desc': rev_act.desc, 'status': 'done'})
                        except Exception as rev_e:
                            rev_tb = ''.join(traceback.format_exception(type(rev_e), rev_e, rev_e.__traceback__))
                            result.reverse_errors.append(f'[rollback all] #{rev_idx} {rev_act.desc}: {rev_e}')
                            self._log.error('Rollback failed for action %d: %s', rev_idx, str(rev_e))
                            _log_write(self._log_file, {'event': 'reverse_all', 'index': rev_idx, 'desc': rev_act.desc, 'status': 'failed', 'error': rev_tb})
                    break

        _log_write(self._log_file, {'event': 'finish', 'success': result.success, 'failed': result.failed, 'decision': result.decision.value if result.decision else None})
        self.finished.emit(result)


class PlanReverseWorker(QtCore.QThread):
    """Reverse actions from a .plan file (iterates in reverse order)."""
    _log = logging.getLogger('flchemist.PlanReverseWorker')
    progress = QtCore.pyqtSignal(int, int)
    finished = QtCore.pyqtSignal(int, list)

    def __init__(self, actions: list, parent=None):
        super().__init__(parent)
        self._actions = actions

    def run(self):
        success = 0
        errors: list = []
        total = len(self._actions)
        for i, act in enumerate(reversed(self._actions), 1):
            try:
                act.reverse()
                success += 1
                self._log.info('Reversed %d/%d: %s', i, total, act.desc)
            except Exception as e:
                tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                errors.append((i, act.desc, tb))
                self._log.error('Reverse failed %d/%d: %s - %s', i, total, act.desc, e)
            self.progress.emit(i, total)
        self.finished.emit(success, errors)
