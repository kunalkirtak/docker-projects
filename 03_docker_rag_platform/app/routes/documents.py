"""
Document ingestion, search, and RAG-context routes.

Ingestion flow (POST /documents):

    FastAPI
       |
       +--> PostgreSQL   (durable metadata: id, title, content, created_at)
       |
       +--> Generate embedding (app/embeddings.py)
               |
               v
             Qdrant       (vector + payload for similarity search)

If the PostgreSQL write succeeds but the Qdrant write fails, the
document row is rolled back so the two stores do not silently
drift out of sync. We do not pretend vector storage succeeded when
it did not.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import vector_store
from app.database import get_db
from app.embeddings import embed_text
from app.models import Document
from app.schemas import (
    ContextItem,
    ContextRequest,
    ContextResponse,
    DocumentCreate,
    DocumentResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

logger = logging.getLogger("app.routes.documents")

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=201)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentResponse:
    document = Document(title=payload.title, content=payload.content)
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        vector = embed_text(f"{payload.title}\n{payload.content}")
        vector_store.upsert_document(
            document_id=document.id,
            vector=vector,
            title=document.title,
            content=document.content,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector store upsert failed for document_id=%s: %s", document.id, exc)
        db.delete(document)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Document could not be indexed in the vector store; the write was rolled back.",
        ) from exc

    return document


@router.get("", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)) -> List[DocumentResponse]:
    return db.query(Document).order_by(Document.id).all()


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    try:
        vector_store.delete_document(document_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Document %s removed from PostgreSQL but Qdrant deletion failed: %s",
            document_id,
            exc,
        )


@router.post("/search", response_model=SearchResponse)
def search_documents(payload: SearchRequest) -> SearchResponse:
    vector = embed_text(payload.query)
    try:
        hits = vector_store.search_documents(vector, limit=payload.limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector search failed: %s", exc)
        raise HTTPException(status_code=502, detail="Vector search is currently unavailable") from exc

    results = [
        SearchResultItem(
            document_id=hit["document_id"],
            title=hit["title"],
            content=hit["content"],
            score=hit["score"],
        )
        for hit in hits
    ]
    return SearchResponse(query=payload.query, results=results)


@router.post("/context", response_model=ContextResponse)
def get_context(payload: ContextRequest) -> ContextResponse:
    """
    Retrieval stage of a Retrieval-Augmented Generation pipeline.

    This endpoint does NOT call a language model. It returns the
    top-K most relevant documents as structured context. A production
    system would pass this context, plus the query, into an LLM
    generation step to produce a final natural-language answer.
    """
    vector = embed_text(payload.query)
    try:
        hits = vector_store.search_documents(vector, limit=payload.limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector search failed during context retrieval: %s", exc)
        raise HTTPException(status_code=502, detail="Vector search is currently unavailable") from exc

    context = [
        ContextItem(
            document_id=hit["document_id"],
            title=hit["title"],
            content=hit["content"],
            score=hit["score"],
        )
        for hit in hits
    ]
    return ContextResponse(query=payload.query, context=context)
