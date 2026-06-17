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
import time

import psutil

from utils import *


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

def calc_size(folder: Path) -> int:
    if not folder.is_dir():  raise ValueError
    if not folder.exists():  raise FileNotFoundError
    return _simple_calc_size(folder)


def wx_check_junction(wx_path: Path, user: str, suffix: str, tar_path: Path, move_backup=True) -> Optional[Exception]:
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
        return UserWarning(f"你为啥要把微信数据目录和指定目录放在同一个磁盘上，这么喜欢{msg_path.anchor}么")
    if move_backup and not backup_path.exists():
        return FileNotFoundError(f"微信备份目录不存在: {backup_path}，你不能移动备份文件")

    tot_size = calc_size(msg_path)
    if tot_size < 1024 * 1024 * 1024 * 2:
        return UserWarning("微信数据目录小于 2GB，迁移必要性不大")

    return None


def wx_draft_junction(wx_path: Path, user: str, suffix: str, tar_path: Path, end_time: str = time.strftime("%Y-%M"), move_backup: bool = True) -> list[Plan]:
    """
    请保证先check再draft！
    :param wx_path: e.g. Path(.../xwechat_files/)
    :param user: e.g. "wxid_qnfywtpg61a022"
    :param suffix: e.g. "4d31"
    :param tar_path: e.g.
    :param end_time: e.g. 2026-04
    :param move_backup: e.g. True
    :return: list[Plan]
    """
    # 请保证先check再draft！
    ret = []
    msg_path = wx_path / (user + suffix) / 'msg'
    backup_path = wx_path / 'Backup' / (user + suffix)
    def _juntion(directory: Path):
        for p in directory.glob(r'20[0-9][0-9]-[0-1][0-9]/'):
            if p.name < end_time and p.is_dir():
                new_name = encode_to_filename(str(directory.relative_to(wx_path) / p.name))
                ret.append(Junc(src=p, dst=tar_path / new_name))

    _juntion(msg_path / 'file')
    _juntion(msg_path / 'video')
    for chat in (msg_path / 'attach').iterdir():
        if chat.is_dir():
            _juntion(chat)

    if move_backup:
        new_name = encode_to_filename(str(backup_path.relative_to(wx_path)))
        ret.append(Junc(src=backup_path, dst=tar_path / new_name))
    return ret





if __name__ == '__main__':
    # a = time.perf_counter()
    # tot_size = calc_size(msg_path)
    # b = time.perf_counter()
    # if tot_size < 1024 * 1024 * 1024 * 2:
    #     warnings.warn("微信数据目录小于 2GB，迁移必要性不大")
    # print(f"耗时: {b - a:.2f}s")
    # create_junction(Path('test/a/'), Path('test/b/b/c/'))
    _ = wx_draft_junction(
        Path(r'D:\Desktop\xwechat_files_copy'),
        r'wxid_qnfywtpg61a022',
        '4d31',
        Path(r'W:/weixin_junc'),
        end_time='2026-02',
        move_backup=True
    )
    print(len(_))
    for i in _[:5]:
        print(i)
    a = time.time()
    try:
        for i, p in enumerate(_):
            ret = p.run()
            if ret:
                print(i, p)
                raise ret
    finally:
        b= time.time()
        print(f"耗时: {b - a:.2f}s")
