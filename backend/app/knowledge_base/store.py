"""Persistent, tenant-filtered Chroma retrieval store."""

from pathlib import Path
import re
import threading

import chromadb

from .chunking import TextChunk
from .embeddings import EmbeddingProtocol, validate_embeddings


COLLECTION_NAME = "a3_knowledge_chunks"


class ChromaRAGStore:
    def __init__(self, vector_db_path: str | Path, embedding: EmbeddingProtocol) -> None:
        path = Path(vector_db_path)
        path.mkdir(parents=True, exist_ok=True)
        self.embedding = embedding
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
        self._close_lock = threading.Lock()
        self._closed = False

    def close(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            self.client.close()
            self._closed = True

    def index_document(
        self,
        user_id: int,
        document_id: int,
        course: str,
        filename: str,
        chunks: list[TextChunk],
    ) -> int:
        if not chunks:
            raise ValueError("chunks must not be empty")
        texts = [chunk.text for chunk in chunks]
        vectors = validate_embeddings(texts, self.embedding.encode(texts))
        self.delete_document(user_id, document_id)
        ids = [f"{document_id}:{index}" for index in range(len(chunks))]
        metadatas = []
        for index, chunk in enumerate(chunks):
            metadata = {
                "user_id": int(user_id),
                "document_id": int(document_id),
                "course": course,
                "filename": filename,
                "source_type": chunk.source_type,
                "chunk_index": index,
                "char_start": int(chunk.char_start),
                "char_end": int(chunk.char_end),
            }
            if chunk.page is not None:
                metadata["page"] = int(chunk.page)
            if chunk.paragraph is not None:
                metadata["paragraph"] = int(chunk.paragraph)
            metadatas.append(metadata)
        try:
            self.collection.upsert(
                ids=ids, documents=texts, embeddings=vectors, metadatas=metadatas
            )
        except Exception:
            self.delete_document(user_id, document_id)
            raise
        return len(chunks)

    def delete_document(self, user_id: int, document_id: int) -> None:
        self.collection.delete(
            where={"$and": [{"user_id": int(user_id)}, {"document_id": int(document_id)}]}
        )

    def count_document(self, user_id: int, document_id: int) -> int:
        result = self.collection.get(
            where={"$and": [{"user_id": int(user_id)}, {"document_id": int(document_id)}]},
            include=[],
        )
        return len(result["ids"])

    def search(
        self, query: str, user_id: int, course: str, top_k: int = 5
    ) -> list[dict]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be blank")
        if type(top_k) is not int or not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        where = {"$and": [{"user_id": int(user_id)}, {"course": course}]}
        existing = self.collection.get(where=where, limit=1, include=[])
        if not existing["ids"]:
            return []
        vectors = validate_embeddings([query], self.embedding.encode([query]))
        result = self.collection.query(
            query_embeddings=vectors,
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        hits = []
        for content, metadata, distance in zip(documents, metadatas, distances):
            chunk_index = int(metadata["chunk_index"])
            document_id = int(metadata["document_id"])
            hits.append(
                {
                    "content": content,
                    "document_id": document_id,
                    "filename": metadata["filename"],
                    "source_type": metadata["source_type"],
                    "page": metadata.get("page"),
                    "paragraph": metadata.get("paragraph"),
                    "char_start": int(metadata["char_start"]),
                    "char_end": int(metadata["char_end"]),
                    "similarity": max(0.0, min(1.0, 1.0 - float(distance))),
                    "citation_id": f"{document_id}:{chunk_index}",
                    "highlight_spans": _highlight_spans(content, query),
                }
            )
        return hits


def _highlight_spans(content: str, query: str) -> list[dict[str, int]]:
    tokens = []
    seen = set()
    for token in re.findall(r"\w+", query, flags=re.UNICODE):
        folded = token.casefold()
        if folded and folded not in seen:
            tokens.append(token)
            seen.add(folded)
    spans = {
        (match.start(), match.end())
        for token in tokens
        for match in re.finditer(re.escape(token), content, flags=re.IGNORECASE)
    }
    return [{"start": start, "end": end} for start, end in sorted(spans)]
