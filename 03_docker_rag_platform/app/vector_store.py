"""
Qdrant vector store abstraction.

The API connects to Qdrant using the Docker Compose service name
"qdrant" as the hostname (see app/config.py), not "localhost".
This mirrors the PostgreSQL connection and is the second concrete
example, in this project, of Docker Compose service discovery via
DNS inside the internal `rag_network`.
"""

import logging
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings

logger = logging.getLogger("app.vector_store")

_client: Optional[QdrantClient] = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=int(settings.qdrant_port))
    return _client


def create_collection() -> None:
    """Create the documents collection if it does not already exist."""
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection in existing:
        return

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=qmodels.VectorParams(
            size=settings.embedding_dim,
            distance=qmodels.Distance.COSINE,
        ),
    )
    logger.info("Created Qdrant collection '%s'", settings.qdrant_collection)


def upsert_document(document_id: int, vector: List[float], title: str, content: str) -> None:
    """Insert or update a document's vector + payload in Qdrant."""
    client = get_client()
    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            qmodels.PointStruct(
                id=document_id,
                vector=vector,
                payload={
                    "document_id": document_id,
                    "title": title,
                    "content": content,
                },
            )
        ],
    )


def search_documents(vector: List[float], limit: int = 5) -> List[dict]:
    """Search for the most similar documents to the given vector."""
    client = get_client()
    hits = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        limit=limit,
    )
    return [
        {
            "document_id": hit.payload.get("document_id"),
            "title": hit.payload.get("title"),
            "content": hit.payload.get("content"),
            "score": hit.score,
        }
        for hit in hits
    ]


def delete_document(document_id: int) -> None:
    """Delete a document's vector from Qdrant by point id."""
    client = get_client()
    try:
        client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=qmodels.PointIdsList(points=[document_id]),
        )
    except UnexpectedResponse as exc:
        logger.warning("Qdrant delete failed for document_id=%s: %s", document_id, exc)
        raise


def is_healthy() -> bool:
    try:
        get_client().get_collections()
        return True
    except Exception as exc:  # noqa: BLE001 - health check must not raise
        logger.warning("Qdrant health check failed: %s", exc)
        return False
