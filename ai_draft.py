"""AI-powered draft: calls DeepSeek API to generate a .plan from user prompt + folder trees."""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import os
from pathlib import Path
from pathlib import Path
from openai import OpenAI, AuthenticationError

from action import action_from_dict

_log = logging.getLogger("flchemist.ai_draft")

SYSTEM_PROMPT = """You are a file-management plan generator. Given folder trees and a user request, output a JSON plan in exactly this format:

{
  "draft": "ai-generated",
  "created_at": "2025-01-01T00:00:00.000000",
  "description": "Human-readable explanation of what this plan does",
  "actions": [
    {
      "__action_cls__": "Move|Copy|Rename",
      "__fields__": { "src": "/full/path/src", "dst": "/full/path/dst" }
    }
  ]
}

Rename uses "name" instead of "dst":
{ "__action_cls__": "Rename", "__fields__": { "src": "/full/path/src", "name": "new-name.ext" } }

Rules:
- Only use Move, Copy, or Rename actions. Never use Junc.
- Use Move for moving files/folders, Copy for copying, Rename for renaming files or directories.
- All paths must be absolute Windows paths (use \\\\\\\\ or /).
- Return ONLY valid JSON, no markdown fences, no extra text before or after.
- "description" should briefly explain in Chinese what the plan achieves.
- Each action must have a real source file/folder that exists in the provided folder trees.
- If the user's request cannot be fulfilled or is ambiguous, set "actions" to an empty list and explain in "description".
"""


def _config_env_path_ai() -> Path:
    return Path(sys.argv[0]).resolve().parent / ".env"


def build_ai_draft(folders: list[Path], prompt: str) -> dict:
    """Call DeepSeek and return a plan dict ready to write as .plan file."""
    _env_path = _config_env_path_ai()
    load_dotenv(_env_path)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("请先配置 DeepSeek API Key：点击左侧「API」按钮，在对话框中输入你的 API Key 并保存")

    # Build folder tree info
    from utils import folder_tree_to_dict
    tree_parts = []
    for f in folders:
        tree = folder_tree_to_dict(f)
        tree_parts.append(json.dumps(tree, ensure_ascii=False, indent=2))
    folder_info = "\n\n---\n\n".join(tree_parts)

    user_content = f"""User request: {prompt}

Folder trees (max 200 entries per folder):
{folder_info}

Generate a file-management plan based on these folders and the user request."""

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    _log.info("Calling DeepSeek API with %d folders, prompt length=%d", len(folders), len(prompt))
    _log.info("--- AI REQUEST ---\nSystem prompt:\n%s\n\nUser content:\n%s", SYSTEM_PROMPT, user_content)
    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=8192,
        )
    except AuthenticationError:
        raise ValueError(
            "API Key 无效或已过期，请检查：\n"
            "1. 点击左侧「API」按钮查看当前 Key\n"
            "2. 确保 Key 没有过期\n"
            "3. 如果问题持续，请前往 https://platform.deepseek.com 重新生成 Key"
        )

    raw = response.choices[0].message.content
    _log.info("--- AI RESPONSE ---\n%s", raw)
    if not raw:
        raise ValueError("Empty response from DeepSeek API")

    # Parse JSON — strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        plan_data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"""AI response is not valid JSON (likely truncated). max_tokens={8192}.
Parsing error: {e}

Raw response (last 500 chars):
...{text[-500:]}"""
        ) from e

    # Validate actions
    actions_raw = plan_data.get("actions", [])
    if not isinstance(actions_raw, list):
        raise ValueError("AI response 'actions' is not a list")

    actions = []
    for a in actions_raw:
        actions.append(action_from_dict(a))

    # Build standard plan format
    result = {
        "draft": "ai-generated",
        "created_at": datetime.now().isoformat(),
        "description": plan_data.get("description", ""),
        "actions": actions_raw,
    }

    _log.info("DeepSeek returned %d actions", len(actions))
    return result
