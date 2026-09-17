"""Minimal policy-document RAG pipeline used by Concierge FAQ responses."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[3]
DOCUMENTS_DIR = ROOT / "knowledge_base" / "documents"


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source: str
    score: float


def chunk_document(text: str, source: str, chunk_size: int = 500, overlap: int = 75) -> List[Dict[str, str]]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + chunk_size]).strip()
        if chunk:
            chunks.append({"text": chunk, "source": source})
    return chunks


class PolicyRetriever:
    """FAISS-backed retriever with lazy FastEmbed model loading."""

    def __init__(
        self,
        documents_dir: Path = DOCUMENTS_DIR,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ):
        self.documents_dir = Path(documents_dir)
        self.model_name = model_name
        self._model = None
        self._index = None
        self._chunks: List[Dict[str, str]] = []

    def _build(self) -> None:
        try:
            import faiss
            from fastembed import TextEmbedding
        except (ImportError, OSError, RuntimeError) as exc:
            raise RuntimeError(
                "RAG dependencies are unavailable; install fastembed and faiss-cpu"
            ) from exc
        try:
            self._model = TextEmbedding(model_name=self.model_name)
            for path in sorted(self.documents_dir.glob("*.md")):
                if path.name.lower() == "readme.md":
                    continue
                self._chunks.extend(
                    chunk_document(path.read_text(encoding="utf-8"), path.name)
                )
            if not self._chunks:
                return
            import numpy as np
            embeddings = self._encode(
                [chunk["text"] for chunk in self._chunks], np
            )
            self._index = faiss.IndexFlatIP(embeddings.shape[1])
            self._index.add(embeddings)
        except (OSError, RuntimeError, ValueError) as exc:
            raise RuntimeError(
                "The RAG embedding model could not be loaded in this environment"
            ) from exc

    def _encode(self, texts: List[str], numpy: Any):
        embeddings = numpy.asarray(list(self._model.embed(texts)), dtype="float32")
        norms = numpy.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / numpy.maximum(norms, 1e-12)

    def score_chunks(self, query: str) -> List[RetrievedChunk]:
        """Return every chunk with its raw cosine/IP similarity score."""
        if not query or not query.strip():
            return []
        if self._index is None and not self._chunks:
            self._build()
        if self._index is None or not self._chunks:
            return []
        import numpy as np
        vector = self._encode([query], np)
        scores, indexes = self._index.search(vector, len(self._chunks))
        return [
            RetrievedChunk(
                self._chunks[index]["text"],
                self._chunks[index]["source"],
                float(score),
            )
            for score, index in zip(scores[0], indexes[0])
            if index >= 0
        ]

    def retrieve(
        self, query: str, top_k: int = 3, min_score: float = 0.72
    ) -> List[RetrievedChunk]:
        scored_chunks = self.score_chunks(query)
        matches = sorted(
            (chunk for chunk in scored_chunks if chunk.score >= min_score),
            key=lambda chunk: chunk.score,
            reverse=True,
        )[:top_k]
        return matches


def answer_faq(query: str, retriever: Optional[PolicyRetriever] = None, top_k: int = 2) -> Dict[str, Any]:
    retriever = retriever or PolicyRetriever()
    try:
        matches = retriever.retrieve(query, top_k=top_k)
    except RuntimeError as exc:
        return {"answer": "I can't verify that from the hotel policies right now.", "sources": [], "error": str(exc)}
    if not matches:
        return {"answer": "I can't verify that from the hotel policies.", "sources": []}
    return {
        "answer": "\n\n".join(match.text for match in matches),
        "sources": [match.source for match in matches],
    }
