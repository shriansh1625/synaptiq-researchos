"""Structured JSON logging with correlation ID support."""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id",
    default=None,
)

_CONFIGURED = False
_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }

        context = getattr(record, "context", None)
        if context:
            payload["context"] = context

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class CorrelationIdFilter(logging.Filter):
    """Attach the active correlation ID to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


class StructuredLogger:
    """Logger wrapper that emits JSON logs at INFO, WARNING, and ERROR."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def info(self, message: str, **context: Any) -> None:
        """Log an informational message."""
        self._log(logging.INFO, message, context)

    def warning(self, message: str, **context: Any) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, message, context)

    def error(self, message: str, **context: Any) -> None:
        """Log an error message."""
        self._log(logging.ERROR, message, context)

    def _log(self, level: int, message: str, context: dict[str, Any]) -> None:
        extra = {"context": context} if context else {}
        self._logger.log(level, message, extra=extra)


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide structured JSON logging."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    normalized_level = level.upper()
    if normalized_level not in _LOG_LEVELS:
        supported = ", ".join(_LOG_LEVELS)
        msg = f"Unsupported log level: {level}. Use one of: {supported}."
        raise ValueError(msg)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(_LOG_LEVELS[normalized_level])

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> StructuredLogger:
    """Return a structured logger for the given module name."""
    if not _CONFIGURED:
        configure_logging()
    return StructuredLogger(logging.getLogger(name))


def set_correlation_id(correlation_id: str) -> contextvars.Token[str | None]:
    """Set the correlation ID for the current context."""
    return correlation_id_var.set(correlation_id)


def get_correlation_id() -> str | None:
    """Return the active correlation ID, if any."""
    return correlation_id_var.get()


def clear_correlation_id(token: contextvars.Token[str | None]) -> None:
    """Reset the correlation ID to its previous value."""
    correlation_id_var.reset(token)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def reset_logging() -> None:
    """Reset logging configuration. Intended for tests."""
    global _CONFIGURED
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
    root_logger.setLevel(logging.WARNING)
    _CONFIGURED = False
    correlation_id_var.set(None)
