"""
-*- coding: utf-8 -*-
@Time    : 2026-06-17
@Github  : windbell0711/flchemist
@File    : utils.py
@Author  : windbell0711
"""

import shutil
from pathlib import Path
import time
import subprocess
import json
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Optional
import base64

FILENAME_PREFIX = "f_"  # 固定前缀，用于避免设备名冲突

def encode_to_filename(raw: str) -> str:
    """
    将任意字符串转换为合法的 Windows 文件名（不含 '.'），转换可逆。
    """
    # UTF-8 编码
    byte_data = raw.encode('utf-8')
    # Base64URL 编码（无填充）
    b64 = base64.urlsafe_b64encode(byte_data).decode('ascii').rstrip('=')
    # 添加前缀
    return FILENAME_PREFIX + b64

def decode_from_filename(encoded: str) -> str:
    """
    从编码后的文件名还原原始字符串。
    """
    if not encoded.startswith(FILENAME_PREFIX):
        raise ValueError("Invalid encoded filename: missing prefix")
    b64 = encoded[len(FILENAME_PREFIX):]
    # 补足填充 '=' 到 4 的倍数
    pad = 4 - (len(b64) % 4)
    if pad != 4:
        b64 += '=' * pad
    # 解码
    byte_data = base64.urlsafe_b64decode(b64)
    return byte_data.decode('utf-8')

def print_tree(directory, depth=-1, prefix="", dir_only=False, exceed=8):
    """
    递归打印目录树形结构
    directory: Path 对象或字符串路径
    prefix: 用于绘制连线的前缀（递归时自动传递）
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return
    if depth == 0:
        return

    # 获取目录内容并排序（文件夹在前，文件在后，按名称排序）
    entries = list(dir_path.iterdir())
    entries.sort(key=lambda x: (not x.is_dir(), x.name))

    # 遍历并打印
    for i, entry in enumerate(entries):
        if i >= exceed:
            print(prefix + "└── ...")
            break

        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "

        # 打印当前条目
        if not dir_only or entry.is_dir():
            print(prefix + connector + entry.name)

        # 如果是文件夹，递归打印内部结构
        if entry.is_dir():
            extension = "    " if is_last else "│   "
            print_tree(entry, depth-1, prefix + extension, dir_only)


@dataclass(frozen=True)
class Plan:
    def run(self) -> Optional[Exception]:
        raise NotImplementedError("u should specify the typ of the plan")
    def reverse(self) -> Optional[Exception]:
        raise NotImplementedError("u should specify the typ of the plan")

@dataclass(frozen=True)
class Copy(Plan):
    src: Path
    dst: Path
    dir_only: bool = False
    def run(self):
        if self.dir_only:
            for root, _, _ in self.src.walk():
                rel_path = root.relative_to(self.src)
                (self.dst / rel_path).mkdir(exist_ok=True)
            return None
        raise NotImplementedError('没写呢')


@dataclass(frozen=True)
class Junc(Plan):
    src: Path
    dst: Path
    def run(self):
        if not self.src.is_dir():
            return FileNotFoundError(f"源目录不存在 {self.src=}")
        if self.dst.exists():
            return FileExistsError(f"目标目录已存在 {self.dst=}")
        # 1. 源文件夹改名
        if (self.src.parent / self.dst.name).exists():
            return FileExistsError("我超我真没想到真会重复啊，上一次处理没跑干净吧")
        original = str(self.src)
        rened = self.src.rename(self.src.parent / self.dst.name)
        # 2. 创建 Junction
        res = subprocess.run(
            ['cmd', '/c', 'mklink', '/J', str(self.src.resolve()), str(self.dst.resolve())],
            capture_output=True,
            text=True,
            shell=False)  # 显式保持 False
        if res.returncode != 0:
            rened.rename(original)  # 回滚
            return RuntimeError(f"创建 Junction 失败: {res.stderr}")
        # 3. 若成功，移动改名后的文件夹
        shutil.move(rened, self.dst)
        return None


if __name__ == '__main__':
    ...
    # print(time.strftime("%Y-%m"))
    # print(Plan(), Junc(src=Path('a'), dst=Path('b')))
    # print_tree(Path('D:/Documents/xwechat_files'), 3, dir_only=True)
    Copy(
        src=Path('D:/Documents/xwechat_files'),
        dst=Path('D:/Desktop/xwechat_files_copy'),
        dir_only=True
    ).run()