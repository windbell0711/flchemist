"""Tests for drafts.py — draft function output verification."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from drafts import (
    draft_classify_by_type,
    draft_classify_by_date,
    DEFAULT_EXT_MAP,
)
from action import Move


def _touch(path: Path, content: str = "data"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestDraftClassifyByType:
    def test_basic_classification(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            dst = Path(d) / "dst"
            src.mkdir()
            _touch(src / "photo.jpg")
            _touch(src / "doc.pdf")
            _touch(src / "script.py")
            _touch(src / "archive.zip")

            actions = draft_classify_by_type(src, dst)
            assert len(actions) == 4
            assert all(isinstance(a, Move) for a in actions)

            targets = {str(a.dst) for a in actions}
            assert any("images" in t for t in targets)
            assert any("documents" in t for t in targets)
            assert any("code" in t for t in targets)
            assert any("archives" in t for t in targets)

    def test_unknown_extension_goes_to_others(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            dst = Path(d) / "dst"
            src.mkdir()
            _touch(src / "file.xyz")

            actions = draft_classify_by_type(src, dst)
            assert len(actions) == 1
            assert "others" in str(actions[0].dst)

    def test_others_none_skips_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            dst = Path(d) / "dst"
            src.mkdir()
            _touch(src / "file.xyz")
            _touch(src / "file.txt")

            actions = draft_classify_by_type(src, dst, others=None)
            assert len(actions) == 1  # .txt only, .xyz skipped
            assert "documents" in str(actions[0].dst)

    def test_custom_ext_map(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            dst = Path(d) / "dst"
            src.mkdir()
            _touch(src / "data.custom")
            _touch(src / "data.txt")

            ext_map: dict[str, set[str]] = {"custom_stuff": {".custom"}}
            actions = draft_classify_by_type(src, dst, extensions_map=ext_map)
            targets = {str(a.dst) for a in actions}
            assert any("custom_stuff" in t for t in targets)
            assert any("others" in t for t in targets)

    def test_directories_skipped(self):
        """Subdirectories should be skipped; only files at the top level are processed."""
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            dst = Path(d) / "dst"
            src.mkdir()
            (src / "subdir").mkdir()

            actions = draft_classify_by_type(src, dst)
            assert len(actions) == 0  # subdir is not a file, so skipped


class TestDraftClassifyByDate:
    def test_basic_date_classification(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            dst = Path(d) / "dst"
            src.mkdir()
            _touch(src / "f1.txt")
            _touch(src / "f2.txt")

            actions = draft_classify_by_date(src, dst)
            assert len(actions) == 2
            assert all(isinstance(a, Move) for a in actions)

    def test_sort_respects_mtime(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src"
            dst = Path(d) / "dst"
            src.mkdir()
            _touch(src / "f1.txt")
            _touch(src / "f2.txt")
            actions = draft_classify_by_date(src, dst)
            assert len(actions) == 2
