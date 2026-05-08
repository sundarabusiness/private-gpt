import re
from itertools import chain
from typing import TYPE_CHECKING, Any, Literal

from injector import inject, singleton
from llama_index.core.indices import VectorStoreIndex
from llama_index.core.schema import BaseNode, NodeWithScore
from llama_index.core.storage import StorageContext
from pydantic import BaseModel, Field

from private_gpt.components.embedding.embedding_component import EmbeddingComponent
from private_gpt.components.llm.llm_component import LLMComponent
from private_gpt.components.node_store.node_store_component import NodeStoreComponent
from private_gpt.components.vector_store.vector_store_component import (
    VectorStoreComponent,
)
from private_gpt.open_ai.extensions.context_filter import ContextFilter
from private_gpt.server.ingest.model import IngestedDoc

if TYPE_CHECKING:
    from llama_index.core.schema import RelatedNodeInfo


FIELD_TOKEN_RE = re.compile(r"\b(?:[A-Z]\d{5}_\d{3}[A-Z]|AADT)\b")


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


class Chunk(BaseModel):
    object: Literal["context.chunk"]
    score: float = Field(examples=[0.023])
    document: IngestedDoc
    text: str = Field(examples=["Outbound sales increased 20%, driven by new leads."])
    previous_texts: list[str] | None = Field(
        default=None,
        examples=[["SALES REPORT 2023", "Inbound didn't show major changes."]],
    )
    next_texts: list[str] | None = Field(
        default=None,
        examples=[
            [
                "New leads came from Google Ads campaign.",
                "The campaign was run by the Marketing Department",
            ]
        ],
    )

    @classmethod
    def from_node(cls: type["Chunk"], node: NodeWithScore) -> "Chunk":
        doc_id = node.node.ref_doc_id if node.node.ref_doc_id is not None else "-"
        return cls(
            object="context.chunk",
            score=node.score or 0.0,
            document=IngestedDoc(
                object="ingest.document",
                doc_id=doc_id,
                doc_metadata=node.metadata,
            ),
            text=node.get_content(),
        )


@singleton
class ChunksService:
    @inject
    def __init__(
        self,
        llm_component: LLMComponent,
        vector_store_component: VectorStoreComponent,
        embedding_component: EmbeddingComponent,
        node_store_component: NodeStoreComponent,
    ) -> None:
        self.vector_store_component = vector_store_component
        self.llm_component = llm_component
        self.embedding_component = embedding_component
        self.storage_context = StorageContext.from_defaults(
            vector_store=vector_store_component.vector_store,
            docstore=node_store_component.doc_store,
            index_store=node_store_component.index_store,
        )

    def _get_sibling_nodes_text(
        self, node_with_score: NodeWithScore, related_number: int, forward: bool = True
    ) -> list[str]:
        explored_nodes_texts = []
        current_node = node_with_score.node
        for _ in range(related_number):
            explored_node_info: RelatedNodeInfo | None = (
                current_node.next_node if forward else current_node.prev_node
            )
            if explored_node_info is None:
                break

            explored_node = self.storage_context.docstore.get_node(
                explored_node_info.node_id
            )

            explored_nodes_texts.append(explored_node.get_content())
            current_node = explored_node

        return explored_nodes_texts

    def retrieve_relevant(
        self,
        text: str,
        context_filter: ContextFilter | None = None,
        limit: int = 10,
        prev_next_chunks: int = 0,
    ) -> list[Chunk]:
        index = VectorStoreIndex.from_vector_store(
            self.vector_store_component.vector_store,
            storage_context=self.storage_context,
            llm=self.llm_component.llm,
            embed_model=self.embedding_component.embedding_model,
            show_progress=True,
        )
        vector_index_retriever = self.vector_store_component.get_retriever(
            index=index, context_filter=context_filter, similarity_top_k=limit
        )
        nodes = vector_index_retriever.retrieve(text)
        nodes.sort(key=lambda n: n.score or 0.0, reverse=True)

        retrieved_nodes = []
        retrieved_nodes.extend(
            self._retrieve_exact_chunks_from_query(text, context_filter, limit)
        )
        for node in nodes:
            chunk = Chunk.from_node(node)
            chunk.previous_texts = self._get_sibling_nodes_text(
                node, prev_next_chunks, False
            )
            chunk.next_texts = self._get_sibling_nodes_text(node, prev_next_chunks)
            if _chunk_identity(chunk) in {_chunk_identity(item) for item in retrieved_nodes}:
                continue
            retrieved_nodes.append(chunk)
            if len(retrieved_nodes) >= limit:
                break

        return retrieved_nodes

    def _retrieve_exact_chunks_from_query(
        self,
        text: str,
        context_filter: ContextFilter | None,
        limit: int,
    ) -> list[Chunk]:
        terms = _extract_field_terms(text)
        exact_chunks: list[Chunk] = []
        seen: set[tuple[str, str]] = set()
        for term in terms:
            for chunk in self.retrieve_by_required_terms([term], context_filter, limit):
                identity = _chunk_identity(chunk)
                if identity in seen:
                    continue
                exact_chunks.append(chunk)
                seen.add(identity)
                if len(exact_chunks) >= limit:
                    return exact_chunks
        return exact_chunks

    def retrieve_by_required_terms(
        self,
        terms: list[str],
        context_filter: ContextFilter | None = None,
        limit: int = 10,
        min_score: float | None = None,
    ) -> list[Chunk]:
        """Return exact source matches when vector recall misses field-name tokens."""
        normalized_terms = [term.strip() for term in terms if term.strip()]
        if not normalized_terms:
            return []

        ref_docs = self.storage_context.docstore.get_all_ref_doc_info()
        if not ref_docs:
            return []

        if context_filter is not None and context_filter.docs_ids is not None:
            ref_docs = {
                doc_id: ref_doc
                for doc_id, ref_doc in ref_docs.items()
                if doc_id in context_filter.docs_ids
            }

        node_ids = list(chain.from_iterable(ref_doc.node_ids for ref_doc in ref_docs.values()))
        nodes = self.storage_context.docstore.get_nodes(node_ids=list(node_ids))
        scored_nodes: list[NodeWithScore] = []
        seen_node_ids: set[str] = set()

        for node in nodes:
            if node.node_id in seen_node_ids:
                continue
            if not _node_matches_all_terms(node, normalized_terms):
                continue

            score = _node_exact_score(node, normalized_terms)
            if min_score is not None and score < min_score:
                continue

            scored_nodes.append(NodeWithScore(node=node, score=score))
            seen_node_ids.add(node.node_id)

        scored_nodes.sort(key=lambda item: item.score or 0.0, reverse=True)
        return [Chunk.from_node(node) for node in scored_nodes[:limit]]


def _node_matches_all_terms(node: BaseNode, terms: list[str]) -> bool:
    metadata = node.metadata or {}
    parts = [
        node.get_content(),
        node.node_id,
        node.ref_doc_id,
        *_flatten_metadata(metadata),
    ]
    source_text = "\n".join(part for part in parts if part).casefold()
    return all(term.casefold() in source_text for term in terms)


def _node_exact_score(node: BaseNode, terms: list[str]) -> float:
    metadata = node.metadata or {}
    file_name = str(metadata.get("file_name") or "").casefold()
    content = node.get_content().casefold()
    score = 1.0

    for term in terms:
        normalized = term.casefold()
        if normalized in file_name:
            score += 4.0
        if normalized in content:
            score += 1.0

    if file_name.startswith("census-acs5-") or file_name.startswith("fhwa-hpms-"):
        score += 3.0
    if file_name == "d7-grounding-source-index.md":
        score += 2.0

    return score


def _extract_field_terms(text: str) -> list[str]:
    terms: list[str] = []
    for match in FIELD_TOKEN_RE.finditer(text):
        term = match.group(0)
        if term not in terms:
            terms.append(term)
    return terms


def _chunk_identity(chunk: Chunk) -> tuple[str, str]:
    return (chunk.document.doc_id, chunk.text)
