"""LangGraph checkpointer factory."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

_CHECKPOINTER: MemorySaver | None = None


def get_checkpointer() -> MemorySaver:
    """Return a process-wide in-memory checkpointer (required for session reads)."""
    global _CHECKPOINTER
    if _CHECKPOINTER is None:
        _CHECKPOINTER = MemorySaver()
    return _CHECKPOINTER


def reset_checkpointer() -> None:
    """Reset the shared checkpointer. Intended for tests."""
    global _CHECKPOINTER
    _CHECKPOINTER = None
