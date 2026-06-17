"""
-*- coding: utf-8 -*-
@Time    : 2026-06-16
@Github  : windbell0711/flchemist
@File    : wx.py
@Author  : windbell0711
"""
import ctypes
import sys
import os
import psutil
from pathlib import Path
import time
import asyncio
import warnings
from contextlib import suppress
from typing import Optional

def is_admin() -> bool:
    """检查当前进程是否具有管理员权限（创建 Junction 需要）"""
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

async def calc_size(folder: Path, timeout: Optional[float] = None) -> int:
    return await asyncio.wait_for(
        asyncio.to_thread(_simple_calc_size, folder),
        timeout=timeout
    )

def move_folder(src: Path, dst: Path) -> None:
    ...

def archive_old_wechat_media(wx_path: Path, user: str, tar_path: Path, move_backup=True) -> None:
    """
    :param wx_path: e.g. Path(.../xwechat_files/)
    :param user: e.g. "wxid_qnfywtpg61a022_4d31"
    :param tar_path: e.g.
    :param move_backup: e.g. True
    :return: None
    """
    if sys.platform != 'win32':
        raise OSError("此功能仅支持 Windows 系统。")
    if ps_is_running('wechat') or ps_is_running('weixin'):
        raise RuntimeError("请关闭微信后再运行此脚本。")

    msg_path = wx_path / user / 'msg'
    backup_path = wx_path / 'Backup' / user

    if not msg_path.exists():
        raise FileNotFoundError(f"微信数据目录不存在: {wx_path}")
    if not tar_path.exists():
        raise FileNotFoundError(f"指定目录不存在: {tar_path}")
    if msg_path.anchor == tar_path.anchor:
        warnings.warn(f"你为啥要把微信数据目录和指定目录放在同一个磁盘上，这么喜欢{msg_path.anchor}么")
    if move_backup and not backup_path.exists():
        raise FileNotFoundError(f"微信备份目录不存在: {backup_path}，你不能移动备份文件")

    tot_size = asyncio.run(calc_size(msg_path, timeout=1))
    if tot_size < 1024 * 1024 * 1024 * 2:
        warnings.warn("微信数据目录小于 2GB，迁移必要性不大")






if __name__ == '__main__':
    msg_path = Path(r'D:\Documents\xwechat_files\wxid_qnfywtpg61a022_4d31\msg')
    a = time.perf_counter()
    tot_size = asyncio.run(calc_size(msg_path, timeout=2.5))
    b = time.perf_counter()
    if tot_size < 1024 * 1024 * 1024 * 2:
        warnings.warn("微信数据目录小于 2GB，迁移必要性不大")
    print(f"耗时: {b - a:.2f}s")