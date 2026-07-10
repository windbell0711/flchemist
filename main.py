"""
-*- coding: utf-8 -*-
@Time    : 2026-06-19
@Github  : windbell0711/flchemist
@File    : main.py
@Author  : windbell0711

flchemist CLI 入口。

子命令：
  plan <draft>    预览 Action 列表（不执行）
  run  <draft>    执行操作
  reverse <log>   回滚操作
  log             查看操作历史
"""

import argparse
import json
import sys
import time
import logging
import traceback
from datetime import datetime
from pathlib import Path

from action import Action, Junc, action_to_dict, action_from_dict
from drafts import draft_classify_by_type, draft_classify_by_date, draft_wechat_junction
from wx import is_admin


LOG_DIR = Path(__file__).parent / 'logs'
PLANS_DIR = Path(__file__).parent / 'plans'

def _log_path(draft_name: str) -> Path:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return LOG_DIR / f'{ts}_{draft_name}.jsonl'

def _plan_path(draft_name: str) -> Path:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    return PLANS_DIR / f'{ts}_{draft_name}.plan'

def _log_write(log_file: Path, entry: dict):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


DRAFT_REGISTRY = {
    'classify-by-type': (draft_classify_by_type, '--src --dst [--ext-map]'),
    'classify-by-date': (draft_classify_by_date, '--src --dst [--pattern]'),
    'wechat-migrate':   (draft_wechat_junction,   '--wx-path --user --suffix --tar-path --end-time'),
}

def cmd_plan(args: argparse.Namespace):
    log = logging.getLogger("flchemist.main")
    log.info("plan command: draft=%s src=%s dst=%s", args.draft, getattr(args, 'src', '?'), getattr(args, 'dst', '?'))
    """生成 Action 列表并保存为计划文件（不执行）。"""
    actions = _build_actions(args)
    if not actions:
        print('(空列表，没有需要执行的操作)')
        return

    plan_file = args.output if args.output else _plan_path(args.draft)
    if isinstance(plan_file, str):
        plan_file = Path(plan_file)
    plan_file.parent.mkdir(parents=True, exist_ok=True)

    plan_data = {
        'draft': args.draft,
        'created_at': datetime.now().isoformat(),
        'actions': [action_to_dict(a) for a in actions],
    }
    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(plan_data, f, ensure_ascii=False, indent=2)

    print(f'共 {len(actions)} 个操作：')
    print('─' * 60)
    for i, act in enumerate(actions, 1):
        print(f'  {i:>4}. {act.desc}')
    print('─' * 60)
    print(f'总计 {len(actions)} 个操作（plan 模式，未执行）')
    print(f'计划文件: {plan_file}')


def cmd_run(args: argparse.Namespace):
    log = logging.getLogger("flchemist.main")
    log.info("run command: planfile=%s", args.planfile)
    """从计划文件读取并执行 Action 列表。"""
    plan_file = Path(args.planfile)
    if not plan_file.is_file():
        print(f'计划文件不存在: {plan_file}', file=sys.stderr)
        sys.exit(1)

    with open(plan_file, 'r', encoding='utf-8') as f:
        plan_data = json.load(f)

    actions = [action_from_dict(a) for a in plan_data['actions']]
    draft_name = plan_data.get('draft', 'unknown')

    if not actions:
        print('(空列表，没有需要执行的操作)')
        return

    _check_dangerous(actions)
    _check_admin_if_needed(actions)

    log_file = _log_path(draft_name)

    print(f'共 {len(actions)} 个操作，日志: {log_file}')
    _log_write(log_file, {'event': 'start', 'draft': draft_name, 'total': len(actions)})

    success = 0
    failed = []

    for i, act in enumerate(actions, 1):
        desc = act.desc
        _log_write(log_file, {'event': 'action_start', 'index': i, 'desc': desc,
                'action_data': action_to_dict(act)})
        print(f'[{i}/{len(actions)}] {desc} ... ', end='', flush=True)

        try:
            act.run()
            print('✓')
            _log_write(log_file, {
                'event': 'action_done', 'index': i, 'desc': desc, 'status': 'done',
            })
            success += 1
        except Exception as e:
            tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            _log_write(log_file, {
                'event': 'action_failed', 'index': i, 'desc': desc,
                'status': 'failed', 'error': tb_str,
            })
            print(f'✗ {e}')
            failed.append((i, act, tb_str))

    _log_write(log_file, {
        'event': 'finish', 'draft': draft_name,
        'success': success, 'failed': len(failed),
    })

    print(f'\n完成: {success} 成功, {len(failed)} 失败')
    if failed:
        print('失败的操作:')
        for idx, act, tb_str in failed:
            print(f'  {idx}. {act.desc}')
            for line in tb_str.strip().split('\n'):
                print(f'       {line}')
        print(f'\n可执行 reverse {log_file} 来回滚已成功的操作。')



def reverse_from_log(log_file):
    log = logging.getLogger("flchemist.reverse")
    log.info("Starting reverse from %s", log_file)
    if not log_file.is_file():
        raise FileNotFoundError(f'log file not found: {log_file}')
    entries = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    done_entries = [e for e in entries if e.get('status') == 'done' and 'action_data' in e]
    done_entries.reverse()
    success = 0
    failed = []
    for i, entry in enumerate(done_entries, 1):
        desc = entry.get('desc', 'unknown')
        try:
            action = action_from_dict(entry['action_data'])
            action.reverse()
            success += 1
            log.debug("Reverse OK: action %d (%s)", i, desc)
        except Exception as e:
            tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            log.error("Reverse failed: action %d (%s): %s", i, desc, str(e))
            failed.append((i, desc, tb_str))
    log.info("Reverse done: %d success, %d failed", success, len(failed))
    return success, failed

def cmd_reverse(args: argparse.Namespace):
    "从日志文件回滚已成功的操作（逆序执行 reverse()）。"
    log_file = Path(args.logfile)
    if not log_file.is_file():
        print(f'日志文件不存在: {log_file}', file=sys.stderr)
        sys.exit(1)
    success, failed = reverse_from_log(log_file)
    if failed:
        print(f'回滚完成: {success} 成功, {len(failed)} 失败')
        print('失败的操作为:')
        for idx, desc, _ in failed:
            print(f'  {idx}. {desc}')
    else:
        print(f'回滚完成: {success} 成功, 0 失败')


def cmd_log(args: argparse.Namespace):
    """查看操作历史。"""
    LOG_DIR.mkdir(exist_ok=True)
    log_files = sorted(LOG_DIR.iterdir(), reverse=True)
    if not log_files:
        print('暂无操作日志。')
        return

    print(f'操作历史（共 {len(log_files)} 条）：')
    print('\u2500' * 60)
    for lf in log_files:
        try:
            with open(lf, 'r', encoding='utf-8') as f:
                first = json.loads(f.readline())
                last = None
                for line in f:
                    line = line.strip()
                    if line:
                        last = json.loads(line)
            draft_name = first.get('draft', '?')
            total = first.get('total', '?')
            if last:
                finish_info = (f' - 成功 {last.get("success", "?")}'
                               f' / 失败 {last.get("failed", "?")}')
            else:
                finish_info = ''
            print(f'  {lf.name}  [{draft_name}]  {total} 操作{finish_info}')
        except Exception:
            print(f'  {lf.name}')


def _build_actions(args: argparse.Namespace) -> list[Action]:
    """根据 draft 参数调用对应的编排函数。"""
    draft_name = args.draft
    fn, _ = DRAFT_REGISTRY.get(draft_name, (None, None))
    if fn is None:
        print(f'未知的 draft: {draft_name}', file=sys.stderr)
        print(f'可用: {", ".join(DRAFT_REGISTRY)}')
        sys.exit(1)

    kwargs = {}
    if draft_name == 'classify-by-type':
        kwargs['src'] = Path(args.src)
        kwargs['dst'] = Path(args.dst)
    elif draft_name == 'classify-by-date':
        kwargs['src'] = Path(args.src)
        kwargs['dst'] = Path(args.dst)
        if args.pattern:
            kwargs['pattern'] = args.pattern
    elif draft_name == 'wechat-migrate':
        kwargs['wx_path'] = Path(args.wx_path)
        kwargs['user'] = args.user
        kwargs['suffix'] = args.suffix
        kwargs['tar_path'] = Path(args.tar_path)
        kwargs['end_time'] = args.end_time
        kwargs['move_backup'] = not args.no_move_backup

    return fn(**kwargs)


def _check_dangerous(actions: list[Action]):
    """检查是否包含 Copy / Junc 等危险操作，提示确认。"""
    dangerous = [a for a in actions if isinstance(a, (Move, Junc))]
    if dangerous:
        print(f'\n警告：该计划包含 {len(dangerous)} 项潜在危险操作（Move / Junc）')
        try:
            reply = input('确定继续？(y/N) ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            reply = 'n'
        if reply != 'y':
            print('已取消')
            sys.exit(0)

def _check_admin_if_needed(actions: list[Action]):
    """检查操作列表中是否包含需要管理员权限的操作（如 Junc）。"""
    if any(isinstance(a, Junc) for a in actions):
        if not is_admin():
            print('警告: Junc 操作需要管理员权限，但当前不是以管理员身份运行！',
                  file=sys.stderr)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger("flchemist.main")
    LOG_DIR.mkdir(exist_ok=True)

    parser = argparse.ArgumentParser(
        prog='flchemist',
        description='Windows 文件批量处理工具',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('plan', help='生成操作计划（不执行）')
    p.add_argument('draft', choices=list(DRAFT_REGISTRY), help='操作类型')
    p.add_argument('--src', type=str, help='源目录（classify-by-* 需要）')
    p.add_argument('--dst', type=str, help='目标目录（classify-by-* 需要）')
    p.add_argument('--pattern', type=str, default='%Y-%m',
                   help='日期格式（classify-by-date 可选，默认 %%Y-%%m）')
    p.add_argument('--wx-path', type=str, help='微信数据目录（wechat-migrate 需要）')
    p.add_argument('--user', type=str, help='微信用户 ID（wechat-migrate 需要）')
    p.add_argument('--suffix', type=str, help='微信用户后缀（wechat-migrate 需要）')
    p.add_argument('--tar-path', type=str, help='目标迁移目录（wechat-migrate 需要）')
    p.add_argument('--end-time', type=str, default=time.strftime('%Y-%m'),
                   help='截止时间，该时间之前的日期数据将被迁移（默认当前月）')
    p.add_argument('--no-move-backup', action='store_true',
                   help='不移动备份目录（wechat-migrate 可选）')
    p.add_argument('--output', '-o', type=str, default=None,
                   help='计划文件输出路径（默认自动生成到 plans/ 目录）')

    p = sub.add_parser('run', help='从计划文件执行操作')
    p.add_argument('planfile', type=str, help='计划文件路径（.plan）')

    p = sub.add_parser('reverse', help='回滚操作')
    p.add_argument('logfile', type=str, help='操作日志文件路径')

    sub.add_parser('log', help='查看操作历史')

    args = parser.parse_args()

    if args.command == 'plan':
        cmd_plan(args)
    elif args.command == 'run':
        cmd_run(args)
    elif args.command == 'reverse':
        cmd_reverse(args)
    elif args.command == 'log':
        cmd_log(args)


if __name__ == '__main__':
    main()
