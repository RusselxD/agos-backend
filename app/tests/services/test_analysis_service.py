import importlib
import json
from types import SimpleNamespace

import httpx
import pytest
from groq import NotFoundError

analysis_service_module = importlib.import_module("app.services.analysis_service")


def _not_found_error(model: str) -> NotFoundError:
    request = httpx.Request(
        "POST", "https://api.groq.com/openai/v1/chat/completions"
    )
    response = httpx.Response(404, request=request)
    return NotFoundError(
        f"Model {model} was not found",
        response=response,
        body={
            "error": {
                "message": f"Model {model} was not found",
                "type": "invalid_request_error",
                "code": "model_not_found",
            }
        },
    )


def _stream_chunk(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=text))]
    )


async def _successful_stream():
    yield _stream_chunk("analysis result")


class FakeCompletions:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requested_models: list[str] = []

    async def create(self, *, model: str, **kwargs):
        self.requested_models.append(model)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def _client(completions: FakeCompletions):
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def _parse_sse(event: str) -> dict:
    return json.loads(event.removeprefix("data: ").strip())


@pytest.mark.asyncio
async def test_model_not_found_uses_next_configured_model(
    monkeypatch: pytest.MonkeyPatch,
):
    completions = FakeCompletions(
        [_not_found_error("retired-model"), _successful_stream()]
    )
    monkeypatch.setattr(
        analysis_service_module,
        "MODELS",
        ["retired-model", "working-model"],
    )
    monkeypatch.setattr(
        analysis_service_module,
        "clients",
        [_client(completions)],
    )

    events = [
        event
        async for event in analysis_service_module.analysis_service._stream_with_fallback(
            messages=[],
            max_tokens=32,
        )
    ]

    assert completions.requested_models == ["retired-model", "working-model"]
    assert [_parse_sse(event) for event in events] == [
        {"text": "analysis result"},
        {"done": True},
    ]


@pytest.mark.asyncio
async def test_unexpected_provider_error_is_returned_as_sse(
    monkeypatch: pytest.MonkeyPatch,
):
    completions = FakeCompletions([RuntimeError("unexpected provider failure")])
    monkeypatch.setattr(analysis_service_module, "MODELS", ["working-model"])
    monkeypatch.setattr(
        analysis_service_module,
        "clients",
        [_client(completions)],
    )

    events = [
        event
        async for event in analysis_service_module.analysis_service._stream_with_fallback(
            messages=[],
            max_tokens=32,
        )
    ]

    assert [_parse_sse(event) for event in events] == [
        {
            "error": "AI analysis is temporarily unavailable. Please try again later.",
            "done": True,
        }
    ]
