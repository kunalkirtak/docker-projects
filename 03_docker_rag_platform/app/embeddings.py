"""
Deterministic, local, hash-based embedding implementation.

IMPORTANT — READ THIS BEFORE REUSING THIS CODE:

This is a DEMONSTRATION embedding function, not a production
semantic embedding model. It exists purely to make the Docker /
RAG infrastructure in this project runnable without:

  * an external embedding API (OpenAI, Cohere, Gemini, ...)
  * downloading a multi-hundred-megabyte transformer model

It works by hashing overlapping word tokens into a fixed-size
vector ("feature hashing" / the "hashing trick"), then L2-normalizing
the result. This means:

  * The SAME text always produces the SAME vector (deterministic).
  * Similar-looking tokens can collide into the same bucket.
  * It has NO learned understanding of language, synonyms, or
    semantics — it cannot tell that "car" and "automobile" are
    related.

For real semantic search you would replace this module with a
proper sentence embedding model, e.g. a `sentence-transformers`
model or an API-based embedding endpoint (OpenAI `text-embedding-3`,
Cohere `embed-english-v3`, etc.), while keeping the rest of the
architecture (Qdrant storage, retrieval, RAG context assembly)
completely unchanged. That swap is called out in the README's
"Future Improvements" section.
"""

import hashlib
import math
import re
from typing import List

from app.config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _hash_bucket(token: str, dim: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % dim


def _sign(token: str) -> float:
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    # Use one hex character to derive a deterministic +1 / -1 sign.
    return 1.0 if int(digest[0], 16) % 2 == 0 else -1.0


def embed_text(text: str, dim: int = None) -> List[float]:
    """Generate a deterministic, fixed-dimension, L2-normalized vector.

    Args:
        text: input text to embed.
        dim: vector dimension. Defaults to settings.embedding_dim (128).

    Returns:
        A list of `dim` floats with L2 norm 1.0 (unless the input
        produces an all-zero vector, e.g. empty text).
    """
    dim = dim or settings.embedding_dim
    vector = [0.0] * dim

    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        bucket = _hash_bucket(token, dim)
        vector[bucket] += _sign(token)

    norm = math.sqrt(sum(component * component for component in vector))
    if norm == 0.0:
        return vector

    return [component / norm for component in vector]
