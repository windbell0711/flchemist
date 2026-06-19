"""
-*- coding: utf-8 -*-
@Time    : 2026-06-16
@Github  : windbell0711/flchemist
@File    : wx.py
@Author  : windbell0711

微信数据迁移工具，依赖 action.py 的 Action 体系。
"""

from __future__ import annotations

import ctypes
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Optional

import psutil

from action import Action, Junc
from utils import encode_to_filename


def is_admin() -> bool:
    """检查当前进程是否具有管理员权限（创建 Junction 需要）。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception as err:
        print(err)
        return False


def ps_is_running(name: str) -> bool:
    for proc in psutil.process_iter(['pid', 'name']):
        with suppress(psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            assert isinstance(proc.info['name'], str)
            if name in proc.info['name'].lower():
                return True
    return False


def _simple_calc_size(folder: Path) -> int:
    total = 0
    with suppress(PermissionError, OSError):
        for root, dirs, files in folder.walk():
            for file in files:
                total += (root / file).stat().st_size
    return total


def calc_size(folder: Path) -> int:
    if not folder.is_dir():
        raise ValueError
    if not folder.exists():
        raise FileNotFoundError
    return _simple_calc_size(folder)


def wx_check_junction(
    wx_path: Path, user: str, suffix: str, tar_path: Path, move_backup: bool = True
) -> Optional[Exception]:
    """检查微信数据迁移前置条件。"""
    if sys.platform != 'win32':
        return OSError("此功能仅支持 Windows 系统。")
    if ps_is_running('wechat') or ps_is_running('weixin'):
        return RuntimeError("请关闭微信后再运行此脚本。")

    msg_path = wx_path / (user + suffix) / 'msg'
    backup_path = wx_path / 'Backup' / (user + suffix)

    if not msg_path.exists():
        return FileNotFoundError(f"微信数据目录不存在: {wx_path}")
    if not tar_path.exists():
        return FileNotFoundError(f"指定目录不存在: {tar_path}")
    if msg_path.anchor == tar_path.anchor:
        return UserWarning(
            f"你为啥要把微信数据目录和指定目录放在同一个磁盘上，这么喜欢{msg_path.anchor}么"
        )
    if move_backup and not backup_path.exists():
        return FileNotFoundError(
            f"微信备份目录不存在: {backup_path}，你不能移动备份文件"
        )

    tot_size = calc_size(msg_path)
    if tot_size < 1024 * 1024 * 1024 * 2:
        return UserWarning("微信数据目录小于 2GB，迁移必要性不大")

    return None


def wx_draft_junction(
    wx_path: Path,
    user: str,
    suffix: str,
    tar_path: Path,
    end_time: str = time.strftime('%Y-%M'),
    move_backup: bool = True,
) -> list[Action]:
    """生成微信数据迁移的 Action 列表（Junction 操作）。

    请保证先 wx_check_junction 再 draft！
    """
    ret: list[Action] = []
    msg_path = wx_path / (user + suffix) / 'msg'
    backup_path = wx_path / 'Backup' / (user + suffix)

    def _juntion(directory: Path):
        for p in directory.glob(r'20[0-9][0-9]-[0-1][0-9]/'):
            if p.name < end_time and p.is_dir():
                new_name = encode_to_filename(
                    str(directory.relative_to(wx_path) / p.name)
                )
                ret.append(Junc(src=p, dst=tar_path / new_name))

    if msg_path.is_dir():
        _juntion(msg_path / 'file')
        _juntion(msg_path / 'video')
        attach_dir = msg_path / 'attach'
        if attach_dir.is_dir():
            for chat in attach_dir.iterdir():
                if chat.is_dir():
                    _juntion(chat)

    if move_backup and backup_path.is_dir():
        new_name = encode_to_filename(str(backup_path.relative_to(wx_path)))
        ret.append(Junc(src=backup_path, dst=tar_path / new_name))

    return ret
