"""Per-role tool wiring for specialist agents."""

from typing import Any

# Server tool — Anthropic runs search inline; no client tool loop.
WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 1,
}

ROLES_WITH_WEB_SEARCH = frozenset({"marketer", "tech", "finance"})


def get_specialist_tools(role: str) -> list[dict[str, Any]] | None:
    """Return Anthropic tool specs for a specialist role, or None."""
    # Client-side tools (calculators, custom APIs, etc.) would need a tool loop — not built yet.
    if role in ROLES_WITH_WEB_SEARCH:
        return [dict(WEB_SEARCH_TOOL)]
    return None
