"""Unit tests for OpenRouter LLM client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import DiscoveryStatus, Sufficiency
from app.schemas.agent_io import DiscoveryOutput
from app.services.llm.openrouter_client import OpenRouterClient


@pytest.mark.asyncio
async def test_openrouter_client_parses_structured_json() -> None:
    """OpenRouter client should parse JSON chat completions into schemas."""
    payload = DiscoveryOutput(
        status=DiscoveryStatus.OK,
        papers=[],
        sufficiency=Sufficiency.INSUFFICIENT,
        discovery_confidence=0.5,
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = ""
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload.model_dump(mode="json"))}}]
    }

    with patch("app.services.llm.openrouter_client.get_settings") as settings_mock:
        settings_mock.return_value.openrouter_api_key = "test-openrouter-key"
        settings_mock.return_value.openrouter_model = "deepseek/deepseek-chat"
        with patch("app.services.llm.openrouter_client.get_discovery_config") as config_mock:
            config_mock.return_value.gemini_temperature = 0.2
            with patch("httpx.AsyncClient.post", return_value=mock_response) as post_mock:
                client = OpenRouterClient()
                result = await client.generate_structured("test prompt", DiscoveryOutput)

    assert result.status == DiscoveryStatus.OK
    post_mock.assert_awaited_once()
    request_json = post_mock.await_args.kwargs["json"]
    assert request_json["model"] == "deepseek/deepseek-chat"
