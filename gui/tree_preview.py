# tree_preview.py
from __future__ import annotations
from pathlib import Path
from typing import Optional
from PyQt6 import QtWidgets, QtGui
from action import Action, Copy, Move, Rename, Junc

class _FakeNode:
    def __init__(self, name: str, is_dir: bool = False):
        self.name = name
        self.is_dir = is_dir
        self.children = {}
        self.moved_away = False
        self.created = False
        self.move_target = None

    def get_or_create_child(self, name, is_dir=False):
        if name not in self.children:
            self.children[name] = _FakeNode(name, is_dir)
        return self.children[name]

def _ensure_path(root, parts, is_file=False):
    node = root
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        node = node.get_or_create_child(part, is_dir=not (is_last and is_file))
    return node

def build_tree(actions):
    root = _FakeNode("(preview)", is_dir=True)
    for act in actions:
        if isinstance(act, (Move, Copy)):
            try:
                sn = _ensure_path(root, list(act.src.parts), is_file=True)
                sn.moved_away = True
                if isinstance(act, Move):
                    dn = _ensure_path(root, list(act.dst.parts), is_file=True)
                    dn.created = True
                    dn.move_target = str(act.src)
            except Exception:
                pass
        elif isinstance(act, Rename):
            try:
                p = list(act.src.parent.parts) + [act.name]
                dn = _ensure_path(root, p, is_file=True)
                dn.created = True
                dn.move_target = act.src.name
                sn = _ensure_path(root, list(act.src.parts), is_file=True)
                sn.moved_away = True
            except Exception:
                pass
        elif isinstance(act, Junc):
            try:
                sn = _ensure_path(root, list(act.src.parts), is_file=False)
                sn.created = True
                sn.move_target = "junction: " + str(act.dst)
            except Exception:
                pass
    return root

def _populate(node, parent_item):
    for name in sorted(node.children.keys()):
        child = node.children[name]
        item = QtWidgets.QTreeWidgetItem()
        suffix = ""
        if child.moved_away and child.move_target:
            suffix = "  " + child.move_target
        elif child.moved_away:
            suffix = "  (removed)"
        elif child.created and child.move_target:
            suffix = "  " + child.move_target
        elif child.created:
            suffix = "  (new)"
        item.setText(0, name + suffix)
        if child.moved_away:
            item.setForeground(0, QtGui.QColor("#888888"))
            f = item.font(0)
            f.setStrikeOut(True)
            item.setFont(0, f)
        elif child.created:
            item.setForeground(0, QtGui.QColor("#2e7d32"))
        if child.is_dir:
            item.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        parent_item.addChild(item)
        _populate(child, item)

class TreePreviewWidget(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Preview"])
        self.setAlternatingRowColors(True)
        self.setAnimated(True)
        self.setIndentation(20)

    def set_actions(self, actions):
        self.clear()
        root_node = build_tree(actions)
        root_item = QtWidgets.QTreeWidgetItem()
        root_item.setText(0, "(preview)")
        self.addTopLevelItem(root_item)
        _populate(root_node, root_item)
        root_item.setExpanded(True)
