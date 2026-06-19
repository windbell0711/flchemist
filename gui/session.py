from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from action import Action
    from gui.models import ExecuteResult


@dataclass
class Session:
    """Shared state carried between GUI phases."""
    actions: list["Action"] = field(default_factory=list)
    plan_file: Optional[Path] = None
    result: Optional["ExecuteResult"] = None
    log_file: Optional[Path] = None
