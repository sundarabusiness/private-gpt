from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from private_gpt.server.chunks.chunks_service import Chunk, ChunksService
from private_gpt.server.d7_retriever.d7_retriever_router import D7RetrieverResponse
from private_gpt.server.ingest.model import IngestedDoc
from tests.fixtures.mock_injector import MockInjector


def _chunk(
    text: str,
    *,
    score: float = 0.88,
    doc_id: str = "doc-1",
    metadata: dict[str, object] | None = None,
) -> Chunk:
    return Chunk(
        object="context.chunk",
        score=score,
        document=IngestedDoc(
            object="ingest.document",
            doc_id=doc_id,
            doc_metadata=metadata or {},
        ),
        text=text,
    )


def test_d7_retriever_returns_supported_source_match(
    test_client: TestClient, injector: MockInjector
) -> None:
    service = MagicMock(spec=ChunksService)
    service.retrieve_relevant.return_value = [
        _chunk(
            "B12345_001A has 92 frontage feet and verified AADT source.",
            metadata={"parcel_id": "B12345_001A"},
        )
    ]
    injector.bind_mock(ChunksService, service)

    response = test_client.post(
        "/v1/d7/privategpt_retriever",
        json={
            "query": "frontage for B12345_001A",
            "parcel_id": "B12345_001A",
        },
    )

    assert response.status_code == 200
    result = D7RetrieverResponse.model_validate(response.json())
    assert result.status == "FOUND"
    assert len(result.data) == 1
    assert result.data[0].matched_terms == ["B12345_001A"]


def test_d7_retriever_returns_empty_for_fabricated_parcel_id(
    test_client: TestClient, injector: MockInjector
) -> None:
    service = MagicMock(spec=ChunksService)
    service.retrieve_relevant.return_value = [
        _chunk(
            "B12345_001A has 92 frontage feet and verified AADT source.",
            metadata={"parcel_id": "B12345_001A"},
        )
    ]
    injector.bind_mock(ChunksService, service)

    response = test_client.post(
        "/v1/d7/privategpt_retriever",
        json={
            "query": "frontage for B99999_999E",
            "parcel_id": "B99999_999E",
        },
    )

    assert response.status_code == 200
    result = D7RetrieverResponse.model_validate(response.json())
    assert result.status == "EMPTY"
    assert result.empty_reason == "no_source_match"
    assert result.data == []


def test_d7_retriever_applies_min_score_filter(
    test_client: TestClient, injector: MockInjector
) -> None:
    service = MagicMock(spec=ChunksService)
    service.retrieve_relevant.return_value = [
        _chunk(
            "B12345_001A weak semantic match.",
            score=0.12,
            metadata={"parcel_id": "B12345_001A"},
        )
    ]
    injector.bind_mock(ChunksService, service)

    response = test_client.post(
        "/v1/d7/privategpt_retriever",
        json={
            "query": "frontage for B12345_001A",
            "parcel_id": "B12345_001A",
            "min_score": 0.5,
        },
    )

    assert response.status_code == 200
    result = D7RetrieverResponse.model_validate(response.json())
    assert result.status == "EMPTY"
    assert result.empty_reason == "no_source_match"

