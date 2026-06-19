"""Tests for action.py — Action run + reverse paired verification."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from action import Action, Copy, Move, Rename, Junc, action_to_dict, action_from_dict


def _touch(path: Path, content: str = "hello"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestCopy:
    def test_copy_file(self, tmp_path: Path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("data", encoding="utf-8")
        Copy(src=src, dst=dst).run()
        assert dst.read_text(encoding="utf-8") == "data"
        Copy(src=src, dst=dst).reverse()
        assert not dst.exists()

    def test_copy_dir_recursive(self, tmp_path: Path):
        src = tmp_path / "src_dir"
        dst = tmp_path / "dst_dir"
        _touch(src / "a" / "f1.txt")
        _touch(src / "b" / "f2.txt")
        Copy(src=src, dst=dst).run()
        assert dst.is_dir()
        assert (dst / "a" / "f1.txt").read_text() == "hello"
        assert (dst / "b" / "f2.txt").read_text() == "hello"

    def test_copy_dir_only(self, tmp_path: Path):
        src = tmp_path / "src_dir2"
        dst = tmp_path / "dst_dir2"
        _touch(src / "sub" / "f.txt")
        Copy(src=src, dst=dst, dir_only=True).run()
        assert (dst / "sub").is_dir()
        assert not (dst / "sub" / "f.txt").is_file()

    def test_copy_src_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            Copy(src=tmp_path / "nonexistent", dst=tmp_path / "x").run()

    def test_copy_no_tmp_residue(self, tmp_path: Path):
        """成功执行后不应残留 .fltmp 临时文件。"""
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("data")
        Copy(src=src, dst=dst).run()
        assert not any(p.suffix == ".fltmp" for p in tmp_path.rglob("*"))


class TestMove:
    def test_move_file(self, tmp_path: Path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("data", encoding="utf-8")
        Move(src=src, dst=dst).run()
        assert not src.exists()
        assert dst.read_text(encoding="utf-8") == "data"

    def test_move_dir(self, tmp_path: Path):
        src = tmp_path / "src_dir"
        dst = tmp_path / "dst_dir"
        _touch(src / "f.txt")
        Move(src=src, dst=dst).run()
        assert not src.exists()
        assert (dst / "f.txt").read_text() == "hello"

    def test_move_dst_exists(self, tmp_path: Path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("a", encoding="utf-8")
        dst.write_text("b", encoding="utf-8")
        with pytest.raises(FileExistsError):
            Move(src=src, dst=dst).run()

    def test_move_reverse(self, tmp_path: Path):
        src = tmp_path / "src_f"
        dst = tmp_path / "dst_f"
        _touch(src / "f.txt")
        Move(src=src, dst=dst).run()
        assert not src.exists()
        assert dst.is_dir()
        Move(src=src, dst=dst).reverse()
        assert src.is_dir()
        assert not dst.exists()

    def test_move_spaces_in_path(self, tmp_path: Path):
        src = tmp_path / "my folder" / "my file.txt"
        dst = tmp_path / "my folder 2" / "my file.txt"
        _touch(src)
        Move(src=src, dst=dst).run()
        assert dst.read_text() == "hello"


class TestRename:
    def test_rename_file(self, tmp_path: Path):
        src = tmp_path / "old.txt"
        src.write_text("data", encoding="utf-8")
        Rename(src=src, name="new.txt").run()
        assert not src.exists()
        assert (tmp_path / "new.txt").read_text() == "data"

    def test_rename_dir(self, tmp_path: Path):
        src = tmp_path / "old_dir"
        _touch(src / "f.txt")
        Rename(src=src, name="new_dir").run()
        assert not src.exists()
        assert (tmp_path / "new_dir" / "f.txt").read_text() == "hello"

    def test_rename_reverse(self, tmp_path: Path):
        src = tmp_path / "old.txt"
        src.write_text("data", encoding="utf-8")
        Rename(src=src, name="new.txt").run()
        Rename(src=tmp_path / "new.txt", name="old.txt").run()
        assert src.read_text() == "data"
        assert not (tmp_path / "new.txt").exists()

    def test_rename_dst_exists(self, tmp_path: Path):
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("a", encoding="utf-8")
        dst.write_text("b", encoding="utf-8")
        with pytest.raises(FileExistsError):
            Rename(src=src, name="b.txt").run()


class TestJunc:
    def test_junc_not_windows(self):
        if sys.platform.startswith("win"):
            return
        src = Path(tempfile.mkdtemp()) / "junc_src"
        dst = Path(tempfile.mkdtemp()) / "junc_dst"
        with pytest.raises(Exception):
            Junc(src=src, dst=dst).run()

    def test_junc_reverse_no_junc(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            Junc(src=tmp_path / "missing", dst=tmp_path / "data").reverse()


class TestDesc:
    def test_copy_desc(self):
        assert "复制" in Copy(src=Path("a"), dst=Path("b")).desc

    def test_move_desc(self):
        assert "移动" in Move(src=Path("a"), dst=Path("b")).desc

    def test_rename_desc(self):
        assert "重命名" in Rename(src=Path("a/x.txt"), name="y.txt").desc

    def test_junc_desc(self):
        assert "Junction" in Junc(src=Path("a"), dst=Path("b")).desc

class TestSerialization:
    def test_copy_roundtrip(self):
        a = Copy(src=Path(r"C:\src\a.txt"), dst=Path(r"D:\dst\a.txt"))
        data = action_to_dict(a)
        restored = action_from_dict(data)
        assert type(restored) is type(a)
        assert restored.src == a.src
        assert restored.dst == a.dst
        assert restored.dir_only == a.dir_only
        assert restored.desc == a.desc

    def test_move_roundtrip(self):
        a = Move(src=Path(r"C:\src\a.txt"), dst=Path(r"D:\dst\a.txt"))
        data = action_to_dict(a)
        restored = action_from_dict(data)
        assert type(restored) is type(a)
        assert restored.src == a.src
        assert restored.dst == a.dst

    def test_rename_roundtrip(self):
        a = Rename(src=Path(r"C:\src\old.txt"), name="new.txt")
        data = action_to_dict(a)
        restored = action_from_dict(data)
        assert type(restored) is type(a)
        assert restored.src == a.src
        assert restored.name == a.name

    def test_junc_roundtrip(self):
        a = Junc(src=Path(r"C:\data\wx"), dst=Path(r"D:\data\wx"))
        data = action_to_dict(a)
        restored = action_from_dict(data)
        assert type(restored) is type(a)
        assert restored.src == a.src
        assert restored.dst == a.dst

    def test_unknown_class_raises(self):
        import pytest
        with pytest.raises(ValueError, match="未知的 Action 类"):
            action_from_dict({'__action_cls__': 'NonExistent', '__fields__': {}})

    def test_json_compatible(self):
        import json
        a = Move(src=Path(r"C:\src\doc.pdf"), dst=Path(r"D:\dst\doc.pdf"))
        data = action_to_dict(a)
        # Must be JSON-serializable
        json_str = json.dumps(data, ensure_ascii=False)
        restored = json.loads(json_str)
        assert restored['__action_cls__'] == 'Move'
        assert restored['__fields__']['src'] == r'C:\src\doc.pdf'
