"""Domain-specific exceptions for the research pipeline."""

from __future__ import annotations


class SynaptiqError(Exception):
    """Base application error."""


class UpstreamError(SynaptiqError):
    """An external dependency failed after retries."""


class RateLimitError(UpstreamError):
    """Upstream rate limit exceeded."""


class SourceUnavailableError(UpstreamError):
    """A paper source is temporarily unavailable."""


class AgentExecutionError(SynaptiqError):
    """An agent failed to produce valid output."""


class FabricationError(AgentExecutionError):
    """LLM output referenced papers not present in candidates."""


class SchemaValidationError(AgentExecutionError):
    """Structured output failed schema validation."""
