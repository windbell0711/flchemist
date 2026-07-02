"""
-*- coding: utf-8 -*-
@Time    : 2026-06-17
@Github  : windbell0711/flchemist
@File    : utils.py
@Author  : windbell0711

工具函数：文件名编解码、目录树打印等。
"""

from __future__ import annotations

import base64
from pathlib import Path

FILENAME_PREFIX = "f_"


def encode_to_filename(raw: str) -> str:
    """将任意字符串转换为合法的 Windows 文件名（不含 '.'），转换可逆。"""
    byte_data = raw.encode('utf-8')
    b64 = base64.urlsafe_b64encode(byte_data).decode('ascii').rstrip('=')
    return FILENAME_PREFIX + b64


def decode_from_filename(encoded: str) -> str:
    """从编码后的文件名还原原始字符串。"""
    if not encoded.startswith(FILENAME_PREFIX):
        raise ValueError("Invalid encoded filename: missing prefix")
    b64 = encoded[len(FILENAME_PREFIX):]
    pad = 4 - (len(b64) % 4)
    if pad != 4:
        b64 += '=' * pad
    byte_data = base64.urlsafe_b64decode(b64)
    return byte_data.decode('utf-8')


def print_tree(directory, depth=-1, prefix="", dir_only=False, exceed=8):
    """递归打印目录树形结构。"""
    dir_path = Path(directory)
    if not dir_path.is_dir() or depth == 0:
        return
    entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    for i, entry in enumerate(entries):
        if i >= exceed:
            print(prefix + "\u2514\u2500\u2500 ...")
            break
        is_last = (i == len(entries) - 1)
        connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
        if not dir_only or entry.is_dir():
            print(prefix + connector + entry.name)
        if entry.is_dir():
            extension = "    " if is_last else "\u2502   "
            print_tree(entry, depth - 1, prefix + extension, dir_only)

def folder_tree_to_dict(path, max_entries=200):
    """Return a JSON-serializable dict of the directory tree."""
    counter = 0
    def _walk(p):
        nonlocal counter
        if counter >= max_entries:
            return None
        if not p.exists():
            return None
        stat = p.stat()
        entry = {'name': p.name, 'path': str(p.resolve()), 'is_dir': p.is_dir(), 'size': stat.st_size if p.is_file() else 0}
        counter += 1
        if p.is_dir():
            children = []
            try:
                for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    kid = _walk(child)
                    if kid is not None:
                        children.append(kid)
            except PermissionError:
                children.append({'name': '(access denied)', 'path': '', 'is_dir': False, 'size': 0})
            entry['children'] = children
        return entry
    result = _walk(path)
    return result or {'name': str(path), 'path': str(path.resolve()), 'is_dir': True, 'size': 0, 'children': []}
