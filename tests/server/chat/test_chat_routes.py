import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from private_gpt.open_ai.openai_models import OpenAICompletion, OpenAIMessage
from private_gpt.server.chat.chat_router import ChatBody
from private_gpt.server.chunks.chunks_service import Chunk, ChunksService
from private_gpt.server.ingest.model import IngestedDoc
from tests.fixtures.mock_injector import MockInjector


def _chunk(text: str, file_name: str) -> Chunk:
    return Chunk(
        object="context.chunk",
        score=1.0,
        document=IngestedDoc(
            object="ingest.document",
            doc_id="doc-1",
            doc_metadata={"file_name": file_name},
        ),
        text=text,
    )


def test_chat_route_produces_a_stream(test_client: TestClient) -> None:
    body = ChatBody(
        messages=[OpenAIMessage(content="test", role="user")],
        use_context=False,
        stream=True,
    )
    response = test_client.post("/v1/chat/completions", json=body.model_dump())

    raw_events = response.text.split("\n\n")
    events = [
        item.removeprefix("data: ") for item in raw_events if item.startswith("data: ")
    ]
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert len(events) > 0
    assert events[-1] == "[DONE]"


def test_chat_route_produces_a_single_value(test_client: TestClient) -> None:
    body = ChatBody(
        messages=[OpenAIMessage(content="test", role="user")],
        use_context=False,
        stream=False,
    )
    response = test_client.post("/v1/chat/completions", json=body.model_dump())

    # No asserts, if it validates it's good
    OpenAICompletion.model_validate(response.json())
    assert response.status_code == 200


def test_chat_route_d7_grounding_guard_returns_exact_schema(
    test_client: TestClient, injector: MockInjector
) -> None:
    service = MagicMock(spec=ChunksService)
    service.retrieve_by_required_terms.return_value = [
        _chunk(
            '"name": "B01001_001E", "label": "Estimate!!Total:"',
            "census-acs5-2023-B01001_001E.json",
        )
    ]
    injector.bind_mock(ChunksService, service)
    body = ChatBody(
        messages=[
            OpenAIMessage(
                content="You are a zero-hallucination grounding engine.",
                role="system",
            ),
            OpenAIMessage(
                content="Return ONLY grounded excerpts for B01001_001E.",
                role="user",
            ),
        ],
        use_context=True,
        stream=False,
    )

    response = test_client.post("/v1/chat/completions", json=body.model_dump())

    assert response.status_code == 200
    completion = OpenAICompletion.model_validate(response.json())
    content = completion.choices[0].message.content
    assert content is not None
    payload = json.loads(content)
    assert payload["grounded_excerpts"] == [
        '"name": "B01001_001E", "label": "Estimate!!Total:"'
    ]
    assert payload["citations"][0]["field"] == "B01001_001E"
