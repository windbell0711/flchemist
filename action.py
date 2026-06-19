"""
-*- coding: utf-8 -*-
@Time    : 2026-06-19
@Github  : windbell0711/flchemist
@File    : action.py
@Author  : windbell0711

Action 体系：一组可组合、可逆的原子文件操作单元。
每个 Action.run() 保证：失败时不留下自己的残片。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Action:
    def run(self) -> None:
        raise NotImplementedError

    def reverse(self) -> None:
        raise NotImplementedError

    @property
    def desc(self) -> str:
        raise NotImplementedError


# ── 内部辅助 ──────────────────────────────────────────────────

def _cleanup_path(p: Path):
    """删除文件或整个目录，忽略不存在的错误。"""
    if not p.exists():
        return
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    else:
        p.unlink(missing_ok=True)

def _atomic_copy_file(src: Path, dst: Path):
    """同卷原子写入：先写 .tmp 再 rename。失败时清理临时 .tmp。"""
    tmp = dst.with_suffix(dst.suffix + '.fltmp')
    try:
        shutil.copy2(src, tmp)
        tmp.rename(dst)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# ── Copy ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Copy(Action):
    src: Path
    dst: Path
    dir_only: bool = False

    @property
    def desc(self) -> str:
        kind = "目录结构（不含文件）" if self.dir_only else "文件/目录（含文件）"
        return f'复制 {kind} "{self.src}" -> "{self.dst}"'

    def run(self) -> None:
        if not self.src.exists():
            raise FileNotFoundError(f"源路径不存在: {self.src}")

        if self.dir_only:
            if not self.src.is_dir():
                raise NotADirectoryError(f"dir_only 需要源路径是目录: {self.src}")
            created: list[Path] = []
            try:
                for root, _, _ in self.src.walk():
                    rel_path = root.relative_to(self.src)
                    target = self.dst / rel_path
                    target.mkdir(parents=True, exist_ok=True)
                    created.append(target)
            except BaseException:
                for d in reversed(created):
                    _cleanup_path(d)
                raise
            return

        if self.src.is_file():
            self.dst.parent.mkdir(parents=True, exist_ok=True)
            _atomic_copy_file(self.src, self.dst)
        elif self.src.is_dir():
            try:
                shutil.copytree(self.src, self.dst, dirs_exist_ok=True)
            except BaseException:
                _cleanup_path(self.dst)
                raise

    def reverse(self) -> None:
        _cleanup_path(self.dst)


# ── Move ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Move(Action):
    src: Path
    dst: Path

    @property
    def desc(self) -> str:
        return f'移动 "{self.src}" -> "{self.dst}"'

    def run(self) -> None:
        if not self.src.exists():
            raise FileNotFoundError(f"源路径不存在: {self.src}")
        if self.dst.exists():
            raise FileExistsError(f"目标路径已存在: {self.dst}")

        self.dst.parent.mkdir(parents=True, exist_ok=True)

        # 同卷：rename 是原子的，一步到位
        try:
            self.src.rename(self.dst)
            return
        except OSError:
            pass  # 跨卷，fallthrough

        # 跨卷：Copy + 删源，Copy 失败时清理 dst
        try:
            if self.src.is_file():
                _atomic_copy_file(self.src, self.dst)
                self.src.unlink()
            else:
                shutil.copytree(self.src, self.dst, dirs_exist_ok=True)
                shutil.rmtree(self.src)
        except BaseException:
            _cleanup_path(self.dst)
            raise

    def reverse(self) -> None:
        if not self.dst.exists():
            raise FileNotFoundError(f"目标路径不存在，无法回滚: {self.dst}")
        self.src.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.dst.rename(self.src)
            return
        except OSError:
            pass  # 跨卷，fallthrough

        try:
            if self.dst.is_file():
                _atomic_copy_file(self.dst, self.src)
                self.dst.unlink()
            else:
                shutil.copytree(self.dst, self.src, dirs_exist_ok=True)
                shutil.rmtree(self.dst)
        except BaseException:
            _cleanup_path(self.src)
            raise


# ── Rename ────────────────────────────────────────────────────

@dataclass(frozen=True)
class Rename(Action):
    """重命名文件或目录。rename 本身是原子操作，失败无残片。"""
    src: Path
    name: str

    @property
    def desc(self) -> str:
        return f'重命名 "{self.src}" -> "{self.name}"'

    def run(self) -> None:
        new_path = self.src.parent / self.name
        if not self.src.exists():
            raise FileNotFoundError(f"源路径不存在: {self.src}")
        if new_path.exists():
            raise FileExistsError(f"目标文件已存在: {new_path}")
        self.src.rename(new_path)

    def reverse(self) -> None:
        new_path = self.src.parent / self.name
        if not new_path.exists():
            raise FileNotFoundError(f"目标路径不存在，无法回滚: {new_path}")
        new_path.rename(self.src)


# ── Junc ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Junc(Action):
    """创建 NTFS Junction 点（仅 Windows 目录符号链接）。

    三步流程，每一步失败都���干净回滚。
    """
    src: Path
    dst: Path

    @property
    def desc(self) -> str:
        return f'迁移 Junction "{self.src}" -> "{self.dst}"'

    def run(self) -> None:
        if not self.src.is_dir():
            raise FileNotFoundError(f"源目录不存在 {self.src=}")
        if self.dst.exists():
            raise FileExistsError(f"目标目录已存在 {self.dst=}")

        temp_name = self.src.parent / self.dst.name
        if temp_name.exists():
            raise FileExistsError("临时改名路径已存在，上一次操作可能未清理干净")

        original = str(self.src)
        rened = self.src.rename(temp_name)

        res = subprocess.run(
            ['cmd', '/c', 'mklink', '/J', str(self.src.resolve()), str(self.dst.resolve())],
            capture_output=True, text=True, shell=False,
        )
        if res.returncode != 0:
            rened.rename(original)
            raise RuntimeError(f"创建 Junction 失败: {res.stderr}")

        try:
            shutil.move(str(rened), str(self.dst))
        except BaseException:
            # 删除刚创建的 Junction，恢复原始路径
            r = subprocess.run(
                ['cmd', '/c', 'rmdir', str(self.src.resolve())],
                capture_output=True, text=True, shell=False,
            )
            if r.returncode == 0:
                rened.rename(original)
            # 如果 rmdir 本身失败（权限问题），数据卡在 temp_name，
            # 但不吞掉原始异常——让调用方知道出错的同时也能看到 rmdir 失败原因
            raise

    def reverse(self) -> None:
        if not self.src.exists():
            raise FileNotFoundError(f"Junction 点不存在: {self.src}")
        if not self.dst.exists():
            raise FileNotFoundError(f"数据目录不存在: {self.dst}")

        res = subprocess.run(
            ['cmd', '/c', 'rmdir', str(self.src.resolve())],
            capture_output=True, text=True, shell=False,
        )
        if res.returncode != 0:
            raise RuntimeError(f"删除 Junction 失败: {res.stderr}")

        try:
            shutil.move(str(self.dst), str(self.src))
        except BaseException:
            # 移动失败 → 重建 Junction 以恢复现场
            subprocess.run(
                ['cmd', '/c', 'mklink', '/J', str(self.src.resolve()), str(self.dst.resolve())],
                capture_output=True, shell=False,
            )
            raise


# -- 序列化支持（日志/回滚）----------------------------------------

def action_to_dict(action: Action) -> dict:
    """将 Action 序列化为 JSON 兼容的 dict。"""
    cls_name = type(action).__name__
    out: dict[str, object] = {}
    for f in fields(action):
        val = getattr(action, f.name)
        out[f.name] = str(val) if isinstance(val, Path) else val
    return {'__action_cls__': cls_name, '__fields__': out}

def action_from_dict(data: dict) -> Action:
    """从 action_to_dict 的输出重建 Action 实例。"""
    cls_name = data['__action_cls__']
    fields_data = data['__fields__']
    path_fields = {'src', 'dst', 'tar_path', 'wx_path'}
    kwargs = {
        k: Path(v) if k in path_fields else v
        for k, v in fields_data.items()
    }
    cls_map = {c.__name__: c for c in Action.__subclasses__()}
    if cls_name not in cls_map:
        raise ValueError(f'未知的 Action 类: {cls_name}')
    return cls_map[cls_name](**kwargs)
