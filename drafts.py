"""
-*- coding: utf-8 -*-
@Time    : 2026-06-19
@Github  : windbell0711/flchemist
@File    : drafts.py
@Author  : windbell0711

Draft 编排函数：返回 list[Action]，纯函数无副作用。
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

from action import Action, Move, Junc
from utils import encode_to_filename


# 默认扩展名分类映射（扩展名全部小写）
DEFAULT_EXT_MAP: dict[str, set[str]] = {
    'images':     {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff'},
    'documents':  {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                   '.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml'},
    'videos':     {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.ts'},
    'audio':      {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'},
    'archives':   {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso'},
    'code':       {'.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c',
                   '.h', '.go', '.rs', '.sh', '.bat', '.ps1', '.sql'},
}


def _resolve_conflict(target: Path) -> Path:
    """如果 target 已存在，自动追加数字后缀。"""
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    for i in range(1, 100):
        candidate = parent / f'{stem}_{i}{suffix}'
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"冲突过多，无法自动重命名: {target}")


def draft_classify_by_type(
    src: Path,
    dst: Path,
    extensions_map: Optional[dict[str, set[str]]] = None,
    others: str = 'others',
) -> list[Action]:
    """按文件扩展名分类整理文件到子目录。
    :param src: 源目录
    :param dst: 目标根目录（每个分类在其下创建子目录）
    :param extensions_map: 自定义分类映射 {类别名: {扩展名集合}}，扩展名须小写
    :param others: 未匹配文件放入的目录名，设为 None 则跳过未匹配的文件
    :return: list[Action]
    """
    if not src.is_dir():
        raise NotADirectoryError(f"源路径不是目录: {src}")

    dst.mkdir(parents=True, exist_ok=True)
    ext_map = extensions_map if extensions_map is not None else DEFAULT_EXT_MAP

    # 构建扩展名 -> 类别 反向映射
    ext_to_cat: dict[str, str] = {}
    for cat, exts in ext_map.items():
        for ext in exts:
            ext_to_cat[ext] = cat

    actions: list[Action] = []
    for entry in src.iterdir():
        if not entry.is_file():
            continue
        cat = ext_to_cat.get(entry.suffix.lower())
        if cat is None:
            if others is None:
                continue
            cat = others
        target_dir = dst / cat
        target_dir.mkdir(parents=True, exist_ok=True)
        actions.append(Move(src=entry, dst=_resolve_conflict(target_dir / entry.name)))

    return actions


def draft_classify_by_date(
    src: Path,
    dst: Path,
    pattern: str = '%Y-%m',
    use_mtime: bool = True,
) -> list[Action]:
    """按文件修改日期分类整理到子目录。
    :param src: 源目录
    :param dst: 目标根目录（每个日期分组在其下创建子目录）
    :param pattern: strftime 格式，默认 '%Y-%m' 按月归类
    :param use_mtime: True 用修改时间，False 用创建时间
    :return: list[Action]
    """
    if not src.is_dir():
        raise NotADirectoryError(f"源路径不是目录: {src}")

    dst.mkdir(parents=True, exist_ok=True)
    attr = 'st_mtime' if use_mtime else 'st_ctime'

    actions: list[Action] = []
    for entry in src.iterdir():
        if not entry.is_file():
            continue
        try:
            stat = entry.stat()
            date_str = datetime.datetime.fromtimestamp(
                getattr(stat, attr)
            ).strftime(pattern)
        except Exception:
            date_str = 'unknown'

        target_dir = dst / date_str
        target_dir.mkdir(parents=True, exist_ok=True)
        actions.append(Move(src=entry, dst=_resolve_conflict(target_dir / entry.name)))

    return actions


def draft_wechat_junction(
    wx_path: Path,
    user: str,
    suffix: str,
    tar_path: Path,
    end_time: str,
    move_backup: bool = True,
) -> list[Action]:
    """生成微信数据目录迁移的 Junction Action 列表。"""
    ret: list[Action] = []
    msg_path = wx_path / (user + suffix) / 'msg'
    backup_path = wx_path / 'Backup' / (user + suffix)

    def _action_for_dir(directory: Path):
        for p in directory.glob(r'20[0-9][0-9]-[0-1][0-9]/'):
            if p.name < end_time and p.is_dir():
                new_name = encode_to_filename(str(directory.relative_to(wx_path) / p.name))
                ret.append(Junc(src=p, dst=tar_path / new_name))

    if msg_path.is_dir():
        _action_for_dir(msg_path / 'file')
        _action_for_dir(msg_path / 'video')
        attach_dir = msg_path / 'attach'
        if attach_dir.is_dir():
            for chat in attach_dir.iterdir():
                if chat.is_dir():
                    _action_for_dir(chat)

    if move_backup and backup_path.is_dir():
        new_name = encode_to_filename(str(backup_path.relative_to(wx_path)))
        ret.append(Junc(src=backup_path, dst=tar_path / new_name))

    return ret
