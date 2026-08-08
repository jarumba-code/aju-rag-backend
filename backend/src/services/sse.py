"""
SSE (Server-Sent Events) formatter for the AJU streaming endpoint.

Supports event types: start, token, citation, metadata, done, error.
"""
import json
from typing import Any, Dict


def format_sse(event_name: str, data: Dict[str, Any]) -> str:
    """
    Format a single SSE frame as:
      event: <event_name>\\n
      data: <json>\\n
      \\n
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_name}\ndata: {payload}\n\n"
