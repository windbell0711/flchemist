
<a href="https://github.com/windbell0711/flchemist">
  <p align="center">
    <img src="flchemist.ico" width="150" height="150">
  </p>
</a>

# flchemist

**Windows 文件批量处理框架** — 一组可组合、可逆的原子文件操作单元（Action）和常用编排函数（Draft）。

> **Data is precious, Operate carefully.**
> 
> **务必务必提前备份重要数据！！！** 

---

## 快速上手

```powershell
# 安装依赖
pip install psutil openai python-dotenv pyqt6

# 1. 生成操作计划（预览 + 保存为 .plan 文件）
python main.py plan classify-by-type --src D:\Downloads --dst D:\Sorted

# 2. 从计划文件执行操作
python main.py run plans/20260619_143000_classify-by-type.plan

# 查看操作历史
python main.py log

# 从日志回滚
python main.py reverse logs/20250619_143000_classify-by-type.jsonl
```


## Quick Start - GUI Mode (Recommended)

```powershell
# Activate venv and launch GUI
.venv\Scripts\python.exe gui_main.py
```

4-Step Workflow: **Draft** (create a plan) → **Open** (load .plan) → **Execute** (run with progress & error handling) → **Revert** (undo actions).
An **Info** button and **API** configuration panel are also available in the sidebar.

New in v0.2: **AI 生成** draft lets you describe your file organization needs in natural language, and the AI generates the plan automatically. Configure your API key in `.env`.

## Quick Start - CLI Mode
## 核心概念

### 工作流

```
plan  <draft> [选项]   ──生成──>  .plan 文件 (JSON, Action 列表)
                                     │
                                     ▼  run <planfile>
                                  执行操作 →  .jsonl 日志
                                               │
                                               ▼  reverse <logfile>
                                            回滚操作
```

三步分离：**plan（计划）→ run（执行）→ reverse（回滚）**，每步产出可审计的文件。

### Action（原子操作）

不可再分的文件操作单元，保证可逆、自愈、纯函数。

| Action     | 说明                 | run() 特性                                                         | reverse()         |
|------------|--------------------|------------------------------------------------------------------|-------------------|
| **Copy**   | 复制文件或目录            | 文件用 shutil.copy2 + 原子 .tmp 写入；目录用 shutil.copytree；支持 dir_only 模式 | 删除目标              |
| **Move**   | 移动文件或目录            | 同卷用 Path.rename（原子）；跨卷 fallback 为 Copy + 删源                      | 逆序执行              |
| **Rename** | 重命名文件或目录           | Path.rename 原子操作                                                 | 反向 rename         |
| **Junc**   | 创建 NTFS Junction 点 | 三步流程，每一步失败可回滚                                                    | 删 Junction + 移回数据 |

### Draft（编排函数）

返回 list[Action] 的纯函数，无副作用。

| Draft                | 说明           | 选项                                              |
|----------------------|--------------|-------------------------------------------------|
| **classify-by-type** | 按扩展名分类       | --src --dst                                      |
| **classify-by-date** | 按修改日期分类      | --src --dst [--pattern %Y-%m]                   |
| **wechat-migrate**   | 微信数据迁移       | --wx-path --user --suffix --tar-path --end-time [--no-move-backup] |
| **ai-generated**     | AI 根据提示词自动生成 | --folders --prompt (GUI only)                   |

## 项目结构

```
flchemist/
├── action.py      # Action 基类 + 子类（Copy / Move / Rename / Junc）
├── drafts.py      # Draft 编排函数
├── wx.py          # 微信辅助（管理员检查、进程检测）
├── main.py        # CLI 入口
├── utils.py       # 文件名编解码、目录树打印、folder_tree_to_dict
├── ai_draft.py     # AI 生成 DeepSeek API 集成
├── .env            # DEEPSEEK_API_KEY
├── gui/            # PyQt6 桌面 GUI 包
├── plans/         # 计划文件（.plan, JSON）
├── logs/          # 操作日志（.jsonl）
├── pyproject.toml
├── flchemist.spec  # PyInstaller 打包配置
└── tests/
    ├── test_action.py   # Action run + reverse + 序列化测试
    └── test_drafts.py   # Draft 路径与计数验证
```

## CLI 参考

```
python main.py plan <draft> [options]      生成操作计划（不执行）
python main.py run  <planfile>              从计划文件执行操作
python main.py reverse <logfile>            回滚操作
python main.py log                          查看操作历史
```

### 子命令示例

```powershell
# 生成计划（自动保存到 plans/ 目录）
python main.py plan classify-by-type --src D:\Downloads --dst D:\Sorted

# 指定输出路径
python main.py plan classify-by-type --src D:\Downloads --dst D:\Sorted -o my_plan.plan

# 按日期分类
python main.py plan classify-by-date --src D:\Photos --dst D:\Photos_Sorted --pattern %Y-%m-%d

# 微信迁移
python main.py plan wechat-migrate --wx-path D:\xwechat_files --user wxid_xxx --suffix _4d31 --tar-path E:\WeChat_Data --end-time 2026-06

# 执行计划
python main.py run plans/20260619_143000_wechat-migrate.plan

# 回滚
python main.py reverse logs/20250619_143000_wechat-migrate.jsonl
```

## 日志与安全

- 每次 `run` 在 `logs/` 下生成 `{timestamp}_{draft_name}.jsonl` 日志
- 每条日志含状态、描述、序列化的 Action 数据
- `reverse` 重建 Action 实例，逆序执行 `reverse()`
- 涉及 Junction 自动检查管理员权限
- 跨卷 Move 以数据安全优先

## 测试

```powershell
pip install pytest
pytest tests/ -v
```

覆盖：Action run+reverse 配对、边界条件、序列化 roundtrip、Draft 路径正确性。

## 依赖

- Python >= 3.14
- psutil >= 7.2（微信进程检测）
- PyQt6 >= 6.11（GUI mode）
- openai >= 2.44（DeepSeek API 调用）
- python-dotenv >= 1.2（.env 配置加载）
- 仅 Windows 支持 Junc（NTFS Junction）
