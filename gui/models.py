from __future__ import annotations

import enum
from pathlib import Path
from typing import Optional


class DraftType(enum.Enum):
    CLASSIFY_BY_TYPE = "classify-by-type"
    CLASSIFY_BY_DATE = "classify-by-date"
    WECHAT_MIGRATE = "wechat-migrate"
    FROM_PLAN_FILE = "from-plan-file"

    def display_name(self) -> str:
        names = {
            DraftType.CLASSIFY_BY_TYPE: "按扩展名分类",
            DraftType.CLASSIFY_BY_DATE: "按修改日期分类",
            DraftType.WECHAT_MIGRATE: "微信数据迁移",
            DraftType.FROM_PLAN_FILE: "从 .plan 文件导入",
        }
        return names[self]

    def description(self) -> str:
        descs = {
            DraftType.CLASSIFY_BY_TYPE: "将源目录中的文件按扩展名归类到目标目录的子目录中",
            DraftType.CLASSIFY_BY_DATE: "将源目录中的文件按修改日期归类到目标目录的子目录中",
            DraftType.WECHAT_MIGRATE: "将微信数据目录通过 NTFS Junction 迁移到其他盘符",
            DraftType.FROM_PLAN_FILE: "从已有的 .plan 文件导入操作列表，直接预览和执行",
        }
        return descs[self]


class ActionStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

    def display_char(self) -> str:
        chars = {
            ActionStatus.PENDING: "⏳",
            ActionStatus.RUNNING: "▶",
            ActionStatus.SUCCESS: "✓",
            ActionStatus.FAILED: "✗",
            ActionStatus.SKIPPED: "⛔",
        }
        return chars[self]


class ExecuteDecision(enum.Enum):
    ABORT = "abort"
    ROLLBACK_ALL = "rollback_all"


class ParamConfig:
    def __init__(self):
        self.draft_type: Optional[DraftType] = None
        self.src: Optional[Path] = None
        self.dst: Optional[Path] = None
        self.ext_map: Optional[dict[str, set[str]]] = None
        self.pattern: str = "%Y-%m"
        self.use_mtime: bool = True
        self.wx_path: Optional[Path] = None
        self.user: str = ""
        self.suffix: str = ""
        self.tar_path: Optional[Path] = None
        self.end_time: str = ""
        self.no_move_backup: bool = False
        self.plan_file: Optional[Path] = None


class ExecuteResult:
    def __init__(self):
        self.total: int = 0
        self.success: int = 0
        self.failed: int = 0
        self.decision: Optional[ExecuteDecision] = None
        self.reverse_errors: list[str] = []
        self.log_file: Optional[Path] = None
        self.plan_file: Optional[Path] = None
