"""
Token counter for xBridge MCP billing and quotas.

Uses tiktoken for accurate counting (compatible with Grok models).
Falls back to rough estimation if tiktoken is unavailable.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


# Grok models use cl100k_base encoding (same as GPT-4)
ENCODING_NAME = "cl100k_base"


def count_tokens(text: str) -> int:
    """Count tokens in a string."""
    if not text:
        return 0

    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.get_encoding(ENCODING_NAME)
            return len(encoding.encode(text))
        except Exception:
            pass

    # Fallback: rough estimation (~4 chars per token)
    return max(1, len(text) // 4)


def count_messages_tokens(messages: list) -> int:
    """Count tokens across a list of chat messages with overhead for chat format."""
    if not TIKTOKEN_AVAILABLE:
        # Fallback rough
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += count_tokens(content) + 4  # rough overhead
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        total += count_tokens(part.get("text", "")) + 4
        return total

    try:
        encoding = tiktoken.get_encoding(ENCODING_NAME)
        total = 0
        for msg in messages:
            # Every message follows <|start|>{role}<|message|>{content}<|end|>
            total += 3  # overhead per message
            role = msg.get("role", "")
            total += len(encoding.encode(role))
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(encoding.encode(content))
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        total += len(encoding.encode(part.get("text", "")))
        total += 3  # every reply is primed with <|start|>assistant<|message|>
        return total
    except Exception:
        # fallback
        total = sum(count_tokens(str(m)) for m in messages)
        return max(1, total)


class UsageTracker:
    """Simple file-based usage tracker for billing/quotas."""

    def __init__(self, storage_path: str = ".grok_usage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.usage_file = self.storage_path / "usage.json"

    def _load(self) -> Dict[str, Any]:
        if self.usage_file.exists():
            try:
                return json.loads(self.usage_file.read_text())
            except Exception:
                return {}
        return {}

    def _save(self, data: Dict[str, Any]):
        self.usage_file.write_text(json.dumps(data, indent=2))

    def record_usage(
        self,
        api_key: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        tool_name: str = "unknown"
    ) -> Dict[str, Any]:
        """Record a single API call."""
        data = self._load()
        key = api_key[:12] + "..."  # don't store full key

        today = datetime.utcnow().strftime("%Y-%m-%d")

        if key not in data:
            data[key] = {}

        if today not in data[key]:
            data[key][today] = {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "tools": {}
            }

        day = data[key][today]
        day["calls"] += 1
        day["prompt_tokens"] += prompt_tokens
        day["completion_tokens"] += completion_tokens

        if tool_name not in day["tools"]:
            day["tools"][tool_name] = 0
        day["tools"][tool_name] += 1

        self._save(data)

        return {
            "date": today,
            "calls_today": day["calls"],
            "total_tokens_today": day["prompt_tokens"] + day["completion_tokens"]
        }

    def get_daily_usage(self, api_key: str, date: str = None) -> Dict[str, Any]:
        """Get usage for a specific day."""
        data = self._load()
        key = api_key[:12] + "..."
        date = date or datetime.utcnow().strftime("%Y-%m-%d")
        return data.get(key, {}).get(date, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})


# Global instance
usage_tracker = UsageTracker()
