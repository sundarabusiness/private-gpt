from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from private_gpt.open_ai.extensions.context_filter import ContextFilter
from private_gpt.server.chunks.chunks_service import Chunk, ChunksService
from private_gpt.server.utils.auth import authenticated

d7_retriever_router = APIRouter(prefix="/v1", dependencies=[Depends(authenticated)])


class D7RetrieverBody(BaseModel):
    query: str = Field(examples=["Verify frontage and AADT for B12345_001A"])
    parcel_id: str | None = Field(default=None, examples=["B12345_001A"])
    required_terms: list[str] = Field(default_factory=list)
    context_filter: ContextFilter | None = None
    limit: int = Field(default=10, ge=1, le=50)
    prev_next_chunks: int = Field(default=0, ge=0, le=5)
    min_score: float | None = Field(default=None, ge=0.0)
    require_source_match: bool = True


class D7RetrievedChunk(BaseModel):
    object: Literal["d7.privategpt_retriever.chunk"]
    matched_terms: list[str]
    chunk: Chunk


class D7RetrieverResponse(BaseModel):
    object: Literal["d7.privategpt_retriever.result"]
    model: Literal["private-gpt"]
    status: Literal["FOUND", "EMPTY"]
    parcel_id: str | None
    required_terms: list[str]
    empty_reason: str | None = None
    data: list[D7RetrievedChunk]


def _flatten_metadata(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        flattened: list[str] = []
        for key, item in value.items():
            flattened.append(str(key))
            flattened.extend(_flatten_metadata(item))
        return flattened
    if isinstance(value, list):
        flattened = []
        for item in value:
            flattened.extend(_flatten_metadata(item))
        return flattened
    return [str(value)]


def _chunk_source_text(chunk: Chunk) -> str:
    metadata = chunk.document.doc_metadata or {}
    parts = [
        chunk.text,
        chunk.document.doc_id,
        *list(chunk.previous_texts or []),
        *list(chunk.next_texts or []),
        *_flatten_metadata(metadata),
    ]
    return "\n".join(part for part in parts if part).casefold()


def _required_terms(body: D7RetrieverBody) -> list[str]:
    terms = [body.parcel_id, *body.required_terms]
    unique_terms: list[str] = []
    for term in terms:
        normalized = (term or "").strip()
        if normalized and normalized not in unique_terms:
            unique_terms.append(normalized)
    return unique_terms


def _matched_terms(chunk: Chunk, terms: list[str]) -> list[str]:
    source_text = _chunk_source_text(chunk)
    return [term for term in terms if term.casefold() in source_text]


@d7_retriever_router.post(
    "/d7/privategpt_retriever",
    tags=["D7 PrivateGPT Retriever"],
)
def d7_privategpt_retriever(
    request: Request, body: D7RetrieverBody
) -> D7RetrieverResponse:
    """Retrieve D7 evidence chunks without generating unsupported claims."""
    service = request.state.injector.get(ChunksService)
    terms = _required_terms(body)
    chunks = service.retrieve_relevant(
        body.query,
        body.context_filter,
        body.limit,
        body.prev_next_chunks,
    )

    results: list[D7RetrievedChunk] = []
    for chunk in chunks:
        if body.min_score is not None and chunk.score < body.min_score:
            continue

        matched = _matched_terms(chunk, terms)
        if body.require_source_match and terms and len(matched) != len(terms):
            continue

        results.append(
            D7RetrievedChunk(
                object="d7.privategpt_retriever.chunk",
                matched_terms=matched,
                chunk=chunk,
            )
        )

    empty_reason = None
    if not results:
        empty_reason = "no_source_match" if chunks else "no_chunks"

    return D7RetrieverResponse(
        object="d7.privategpt_retriever.result",
        model="private-gpt",
        status="FOUND" if results else "EMPTY",
        parcel_id=body.parcel_id,
        required_terms=terms,
        empty_reason=empty_reason,
        data=results,
    )

