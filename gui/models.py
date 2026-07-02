from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class DraftType(enum.Enum):
    CLASSIFY_BY_TYPE = 'classify-by-type'
    CLASSIFY_BY_DATE = 'classify-by-date'
    WECHAT_MIGRATE = 'wechat-migrate'
    AI_GENERATED = 'ai-generated'
    FROM_PLAN_FILE = 'from-plan-file'

    def display_name(self) -> str:
        names = {
            DraftType.CLASSIFY_BY_TYPE: '按扩展名分类',
            DraftType.CLASSIFY_BY_DATE: '按修改日期分类',
            DraftType.WECHAT_MIGRATE: '微信数据迁移',
            DraftType.FROM_PLAN_FILE: '从 .plan 文件导入',
            DraftType.AI_GENERATED: 'AI 生成',
        }
        return names[self]

    def description(self) -> str:
        descs = {
            DraftType.CLASSIFY_BY_TYPE: '将源目录中的文件按扩展名归类到目标目录的子目录中',
            DraftType.CLASSIFY_BY_DATE: '将源目录中的文件按修改日期归类到目标目录的子目录中',
            DraftType.WECHAT_MIGRATE: '将微信数据目录通过 NTFS Junction 迁移到其他盘符',
            DraftType.FROM_PLAN_FILE: '从已有的 .plan 文件导入操作列表，直接预览和执行',
            DraftType.AI_GENERATED: '使用 AI 根据提示词自动生成文件整理计划',
        }
        return descs[self]


class ActionStatus(enum.Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    SKIPPED = 'skipped'

    def display_char(self) -> str:
        chars = {
            ActionStatus.PENDING: '⏳',
            ActionStatus.RUNNING: '▶',
            ActionStatus.SUCCESS: '✓',
            ActionStatus.FAILED: '✗',
            ActionStatus.SKIPPED: '⛔',
        }
        return chars[self]


class ExecuteDecision(enum.Enum):
    ABORT = 'abort'
    ROLLBACK_ALL = 'rollback_all'
    IGNORE = 'ignore'
    IGNORE_ALL = 'ignore_all'


@dataclass
class ParamConfig:
    draft_type: Optional[DraftType] = None
    src: Optional[Path] = None
    dst: Optional[Path] = None
    ext_map: Optional[dict[str, set[str]]] = None
    pattern: str = '%Y-%m'
    use_mtime: bool = True
    wx_path: Optional[Path] = None
    user: str = ''
    suffix: str = ''
    tar_path: Optional[Path] = None
    end_time: str = ''
    no_move_backup: bool = False
    plan_file: Optional[Path] = None
    prompt: str = ''
    folders: list[Path] = field(default_factory=list)


@dataclass
class ExecuteResult:
    total: int = 0
    success: int = 0
    failed: int = 0
    decision: Optional[ExecuteDecision] = None
    reverse_errors: list[str] = field(default_factory=list)
    log_file: Optional[Path] = None
    plan_file: Optional[Path] = None
    prompt: str = ''
    folders: list[Path] = field(default_factory=list)
