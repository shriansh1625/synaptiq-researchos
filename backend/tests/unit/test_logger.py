"""Tests for structured JSON logging."""

from __future__ import annotations

import io
import json
import logging

import pytest

from app.monitoring.logger import (
    CorrelationIdFilter,
    JsonFormatter,
    StructuredLogger,
    clear_correlation_id,
    configure_logging,
    generate_correlation_id,
    get_correlation_id,
    get_logger,
    reset_logging,
    set_correlation_id,
)


@pytest.fixture(autouse=True)
def clean_logging() -> None:
    """Reset logging and correlation context between tests."""
    reset_logging()
    yield
    reset_logging()


def _capture_logger(name: str = "synaptiq.test") -> tuple[logging.Logger, io.StringIO]:
    """Attach a JSON stream handler for assertions."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationIdFilter())

    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger, stream


def test_json_formatter_outputs_valid_json() -> None:
    """JsonFormatter should emit parseable JSON with required fields."""
    logger, stream = _capture_logger()
    logger.info("service started")

    payload = json.loads(stream.getvalue().strip())

    assert payload["level"] == "INFO"
    assert payload["message"] == "service started"
    assert payload["logger"] == "synaptiq.test"
    assert "timestamp" in payload


def test_correlation_id_is_included_in_logs() -> None:
    """Logs should include the active correlation ID."""
    token = set_correlation_id("corr-123")
    try:
        logger = get_logger("synaptiq.correlation")
        buffer = io.StringIO()
        handler = logging.StreamHandler(buffer)
        handler.setFormatter(JsonFormatter())
        handler.addFilter(CorrelationIdFilter())
        logging.getLogger().handlers.clear()
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

        logger.info("processing request")

        payload = json.loads(buffer.getvalue().strip())
        assert payload["correlation_id"] == "corr-123"
    finally:
        clear_correlation_id(token)


def test_structured_logger_supports_info_warning_error_levels() -> None:
    """StructuredLogger should emit INFO, WARNING, and ERROR records."""
    configure_logging("INFO")
    logger = get_logger("synaptiq.levels")

    root = logging.getLogger()
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationIdFilter())
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    lines = [line for line in buffer.getvalue().splitlines() if line.strip()]
    levels = [json.loads(line)["level"] for line in lines]

    assert levels == ["INFO", "WARNING", "ERROR"]


def test_structured_logger_includes_context_fields() -> None:
    """StructuredLogger should attach arbitrary context to JSON logs."""
    logger, stream = _capture_logger("synaptiq.context")
    structured = StructuredLogger(logger)

    structured.info("agent finished", agent="verification", latency_ms=120)

    payload = json.loads(stream.getvalue().strip())

    assert payload["context"] == {"agent": "verification", "latency_ms": 120}


def test_configure_logging_rejects_invalid_level() -> None:
    """configure_logging should reject unsupported log levels."""
    with pytest.raises(ValueError, match="Unsupported log level"):
        configure_logging("VERBOSE")


def test_generate_and_read_correlation_id() -> None:
    """Correlation ID helpers should set and read the active value."""
    assert get_correlation_id() is None

    correlation_id = generate_correlation_id()
    token = set_correlation_id(correlation_id)

    assert get_correlation_id() == correlation_id

    clear_correlation_id(token)
    assert get_correlation_id() is None
