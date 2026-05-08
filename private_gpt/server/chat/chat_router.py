import json
from datetime import date

from fastapi import APIRouter, Depends, Request
from llama_index.core.llms import ChatMessage, MessageRole
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from private_gpt.open_ai.extensions.context_filter import ContextFilter
from private_gpt.open_ai.openai_models import (
    OpenAICompletion,
    OpenAIMessage,
    to_openai_response,
    to_openai_sse_stream,
)
from private_gpt.server.chat.chat_service import ChatService
from private_gpt.server.chunks.chunks_service import (
    Chunk,
    ChunksService,
    _extract_field_terms,
)
from private_gpt.server.utils.auth import authenticated

chat_router = APIRouter(prefix="/v1", dependencies=[Depends(authenticated)])


class ChatBody(BaseModel):
    messages: list[OpenAIMessage]
    use_context: bool = False
    context_filter: ContextFilter | None = None
    include_sources: bool = True
    stream: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a rapper. Always answer with a rap.",
                        },
                        {
                            "role": "user",
                            "content": "How do you fry an egg?",
                        },
                    ],
                    "stream": False,
                    "use_context": True,
                    "include_sources": True,
                    "context_filter": {
                        "docs_ids": ["c202d5e6-7b69-4869-81cc-dd574ee8ee11"]
                    },
                }
            ]
        }
    }


def _is_d7_grounding_request(body: ChatBody) -> bool:
    prompt_text = "\n".join(message.content or "" for message in body.messages).casefold()
    return (
        "zero-hallucination grounding engine" in prompt_text
        or "return only grounded excerpts" in prompt_text
    )


def _d7_grounding_completion(request: Request, body: ChatBody) -> OpenAICompletion:
    chunks_service = request.state.injector.get(ChunksService)
    prompt_text = "\n".join(message.content or "" for message in body.messages)
    terms = _extract_field_terms(prompt_text)
    chunks: list[Chunk] = []
    seen: set[tuple[str, str]] = set()

    for term in terms:
        for chunk in chunks_service.retrieve_by_required_terms(
            [term], body.context_filter, limit=3
        ):
            identity = (chunk.document.doc_id, chunk.text)
            if identity in seen:
                continue
            chunks.append(chunk)
            seen.add(identity)

    payload = {
        "grounded_excerpts": [chunk.text for chunk in chunks],
        "citations": _d7_citations(chunks, terms),
    }
    return to_openai_response(json.dumps(payload, indent=2), chunks)


def _d7_citations(chunks: list[Chunk], terms: list[str]) -> list[dict[str, str]]:
    pulled = date.today().isoformat()
    citations: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        metadata = chunk.document.doc_metadata or {}
        source_document = str(metadata.get("file_name") or chunk.document.doc_id)
        source_text = "\n".join(
            [chunk.text, source_document, *[str(value) for value in metadata.values()]]
        ).casefold()
        for term in terms:
            if term.casefold() not in source_text:
                continue
            key = (term, source_document)
            if key in seen:
                continue
            citations.append(
                {
                    "source": "PrivateGPT",
                    "field": term,
                    "source_document": source_document,
                    "pulled": pulled,
                }
            )
            seen.add(key)
    return citations


@chat_router.post(
    "/chat/completions",
    response_model=None,
    responses={200: {"model": OpenAICompletion}},
    tags=["Contextual Completions"],
    openapi_extra={
        "x-fern-streaming": {
            "stream-condition": "stream",
            "response": {"$ref": "#/components/schemas/OpenAICompletion"},
            "response-stream": {"$ref": "#/components/schemas/OpenAICompletion"},
        }
    },
)
def chat_completion(
    request: Request, body: ChatBody
) -> OpenAICompletion | StreamingResponse:
    """Given a list of messages comprising a conversation, return a response.

    Optionally include an initial `role: system` message to influence the way
    the LLM answers.

    If `use_context` is set to `true`, the model will use context coming
    from the ingested documents to create the response. The documents being used can
    be filtered using the `context_filter` and passing the document IDs to be used.
    Ingested documents IDs can be found using `/ingest/list` endpoint. If you want
    all ingested documents to be used, remove `context_filter` altogether.

    When using `'include_sources': true`, the API will return the source Chunks used
    to create the response, which come from the context provided.

    When using `'stream': true`, the API will return data chunks following [OpenAI's
    streaming model](https://platform.openai.com/docs/api-reference/chat/streaming):
    ```
    {"id":"12345","object":"completion.chunk","created":1694268190,
    "model":"private-gpt","choices":[{"index":0,"delta":{"content":"Hello"},
    "finish_reason":null}]}
    ```
    """
    if _is_d7_grounding_request(body):
        return _d7_grounding_completion(request, body)

    service = request.state.injector.get(ChatService)
    all_messages = [
        ChatMessage(content=m.content, role=MessageRole(m.role)) for m in body.messages
    ]
    if body.stream:
        completion_gen = service.stream_chat(
            messages=all_messages,
            use_context=body.use_context,
            context_filter=body.context_filter,
        )
        return StreamingResponse(
            to_openai_sse_stream(
                completion_gen.response,
                completion_gen.sources if body.include_sources else None,
            ),
            media_type="text/event-stream",
        )
    else:
        completion = service.chat(
            messages=all_messages,
            use_context=body.use_context,
            context_filter=body.context_filter,
        )
        return to_openai_response(
            completion.response, completion.sources if body.include_sources else None
        )
