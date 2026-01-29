import asyncio

import opik
from fastapi import Request
from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchText,
    MatchValue,
    Prefetch,
)

from src.api.models.api_models import SearchResult
from src.infrastructure.qdrant.qdrant_vectorstore import AsyncQdrantVectorStore
from src.utils.logger_util import setup_logging

logger = setup_logging()


from src.utils.security import sanitize_string

@opik.track(name="query_with_filters")
async def query_with_filters(
    request: Request,
    query_text: str = "",
    feed_author: str | None = None,
    feed_name: str | None = None,
    title_keywords: str | None = None,
    category: str | None = None,
    language: str | None = None,
    min_stars: int | None = None,
    source_type: str | None = None,
    limit: int = 5,
) -> list[SearchResult]:
    """Query the vector store with optional filters and return search results.

    Performs a hybrid dense + sparse search on Qdrant and applies filters based
    on feed author, feed name, title keywords, category, language, stars, and source type.
    Results are deduplicated by point ID.

    Args:
        request (Request): FastAPI request object containing the vector store in app.state.
        query_text (str): Text query to search for.
        feed_author (str | None): Optional filter for the feed author (deprecated).
        feed_name (str | None): Optional filter for the feed name (deprecated).
        title_keywords (str | None): Optional filter for title keywords.
        category (str | None): Optional filter for category (Framework, Library, Platform, Tool).
        language (str | None): Optional filter for programming language.
        min_stars (int | None): Optional filter for minimum GitHub stars.
        source_type (str | None): Optional filter for source type.
        limit (int): Maximum number of results to return.

    Returns:
        list[SearchResult]:
            List of search results containing title, source info, URL, chunk text, and score.

    """
    # Sanitize all string inputs to prevent injection attacks
    query_text = sanitize_string(query_text, max_length=2000) if query_text else ""
    feed_author = sanitize_string(feed_author, max_length=200) if feed_author else None
    feed_name = sanitize_string(feed_name, max_length=200) if feed_name else None
    title_keywords = sanitize_string(title_keywords, max_length=500) if title_keywords else None
    category = sanitize_string(category, max_length=100) if category else None
    language = sanitize_string(language, max_length=50) if language else None
    source_type = sanitize_string(source_type, max_length=50) if source_type else None
    
    # Validate limit
    limit = max(1, min(50, limit))  # Ensure limit is between 1 and 50
    
    vectorstore: AsyncQdrantVectorStore = request.app.state.vectorstore
    # Generate embeddings concurrently in thread pool to avoid blocking event loop
    dense_task = asyncio.to_thread(vectorstore.dense_vectors, [query_text])
    sparse_task = asyncio.to_thread(vectorstore.sparse_vectors, [query_text])
    dense_result, sparse_result = await asyncio.gather(dense_task, sparse_task)
    dense_vector = dense_result[0]
    sparse_vector = sparse_result[0]

    # Build filter conditions
    conditions: list[FieldCondition] = []
    
    # Legacy filters (for backward compatibility)
    if feed_author:
        conditions.append(FieldCondition(key="feed_author", match=MatchValue(value=feed_author)))
    if feed_name:
        conditions.append(FieldCondition(key="feed_name", match=MatchValue(value=feed_name)))
    
    # New filters for AI agent tools
    if category:
        conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
    if language:
        conditions.append(FieldCondition(key="language", match=MatchValue(value=language)))
    if min_stars is not None:
        conditions.append(
            FieldCondition(key="stars", range={"gte": min_stars})  # type: ignore
        )
    if source_type:
        conditions.append(FieldCondition(key="source_type", match=MatchValue(value=source_type)))
    
    if title_keywords:
        conditions.append(
            FieldCondition(key="title", match=MatchText(text=title_keywords.strip().lower()))
        )

    query_filter = Filter(must=conditions) if conditions else None  # type: ignore

    fetch_limit = max(1, limit) * 100
    logger.info(f"Fetching up to {fetch_limit} points for unique Ids.")

    response = await vectorstore.client.query_points(
        collection_name=vectorstore.collection_name,
        query=FusionQuery(fusion=Fusion.RRF),
        prefetch=[
            Prefetch(query=dense_vector, using="Dense", limit=fetch_limit, filter=query_filter),
            Prefetch(query=sparse_vector, using="Sparse", limit=fetch_limit, filter=query_filter),
        ],
        query_filter=query_filter,
        limit=fetch_limit,
    )

    # Deduplicate by point ID
    seen_ids: set[str] = set()
    results: list[SearchResult] = []
    for point in response.points:
        if point.id in seen_ids:
            continue
        seen_ids.add(point.id)  # type: ignore
        payload = point.payload or {}
        results.append(
            SearchResult(
                title=payload.get("title", ""),
                # Legacy fields
                feed_author=payload.get("feed_author") or payload.get("source_author"),
                feed_name=payload.get("feed_name") or payload.get("source_name"),
                article_author=payload.get("article_authors") or payload.get("authors"),
                # New fields
                source_name=payload.get("source_name"),
                source_author=payload.get("source_author"),
                authors=payload.get("authors"),
                url=payload.get("url"),
                chunk_text=payload.get("chunk_text"),
                score=point.score,
                category=payload.get("category"),
                language=payload.get("language"),
                stars=payload.get("stars"),
                features=payload.get("features"),
                source_type=payload.get("source_type"),
            )
        )

    results = results[:limit]
    logger.info(f"Returning {len(results)} results for matching query '{query_text}'")
    return results


@opik.track(name="query_unique_titles")
async def query_unique_titles(
    request: Request,
    query_text: str,
    feed_author: str | None = None,
    feed_name: str | None = None,
    title_keywords: str | None = None,
    category: str | None = None,
    language: str | None = None,
    min_stars: int | None = None,
    source_type: str | None = None,
    limit: int = 5,
) -> list[SearchResult]:
    """Query the vector store and return only unique titles.

    Performs a hybrid dense + sparse search with optional filters and dynamically
    increases the fetch limit to account for duplicates. Deduplicates results
    by article/tool title.

    Args:
        request (Request): FastAPI request object containing the vector store in app.state.
        query_text (str): Text query to search for.
        feed_author (str | None): Optional filter for the feed author (deprecated).
        feed_name (str | None): Optional filter for the feed name (deprecated).
        title_keywords (str | None): Optional filter for title keywords.
        category (str | None): Optional filter for category.
        language (str | None): Optional filter for programming language.
        min_stars (int | None): Optional filter for minimum GitHub stars.
        source_type (str | None): Optional filter for source type.
        limit (int): Maximum number of unique results to return.

    Returns:
        list[SearchResult]:
            List of unique search results containing title, source info, URL, chunk text, and score.

    """
    # Sanitize all string inputs to prevent injection attacks
    query_text = sanitize_string(query_text, max_length=2000) if query_text else ""
    feed_author = sanitize_string(feed_author, max_length=200) if feed_author else None
    feed_name = sanitize_string(feed_name, max_length=200) if feed_name else None
    title_keywords = sanitize_string(title_keywords, max_length=500) if title_keywords else None
    category = sanitize_string(category, max_length=100) if category else None
    language = sanitize_string(language, max_length=50) if language else None
    source_type = sanitize_string(source_type, max_length=50) if source_type else None
    
    # Validate limit
    limit = max(1, min(50, limit))  # Ensure limit is between 1 and 50
    
    vectorstore: AsyncQdrantVectorStore = request.app.state.vectorstore
    # Generate embeddings concurrently in thread pool to avoid blocking event loop
    dense_task = asyncio.to_thread(vectorstore.dense_vectors, [query_text])
    sparse_task = asyncio.to_thread(vectorstore.sparse_vectors, [query_text])
    dense_result, sparse_result = await asyncio.gather(dense_task, sparse_task)
    dense_vector = dense_result[0]
    sparse_vector = sparse_result[0]

    # Build filter conditions
    conditions: list[FieldCondition] = []
    
    # Legacy filters (for backward compatibility)
    if feed_author:
        conditions.append(FieldCondition(key="feed_author", match=MatchValue(value=feed_author)))
    if feed_name:
        conditions.append(FieldCondition(key="feed_name", match=MatchValue(value=feed_name)))
    
    # New filters for AI agent tools
    if category:
        conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
    if language:
        conditions.append(FieldCondition(key="language", match=MatchValue(value=language)))
    if min_stars is not None:
        conditions.append(
            FieldCondition(key="stars", range={"gte": min_stars})  # type: ignore
        )
    if source_type:
        conditions.append(FieldCondition(key="source_type", match=MatchValue(value=source_type)))
    
    if title_keywords:
        conditions.append(
            FieldCondition(key="title", match=MatchText(text=title_keywords.strip().lower()))
        )

    query_filter = Filter(must=conditions) if conditions else None  # type: ignore

    # Reduced fetch_limit multiplier from 280 to 50 for better performance
    # 50 should be sufficient to get unique titles while avoiding excessive data fetching
    fetch_limit = max(1, limit) * 50
    logger.info(f"Fetching up to {fetch_limit} points for unique titles.")

    response = await vectorstore.client.query_points(
        collection_name=vectorstore.collection_name,
        query=FusionQuery(fusion=Fusion.RRF),
        prefetch=[
            Prefetch(query=dense_vector, using="Dense", limit=fetch_limit, filter=query_filter),
            Prefetch(query=sparse_vector, using="Sparse", limit=fetch_limit, filter=query_filter),
        ],
        query_filter=query_filter,
        limit=fetch_limit,
    )

    # Deduplicate by title
    seen_titles: set[str] = set()
    results: list[SearchResult] = []
    for point in response.points:
        payload = point.payload or {}
        title = payload.get("title")
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        results.append(
            SearchResult(
                title=title,
                # Legacy fields
                feed_author=payload.get("feed_author") or payload.get("source_author"),
                feed_name=payload.get("feed_name") or payload.get("source_name"),
                article_author=payload.get("article_authors") or payload.get("authors"),
                # New fields
                source_name=payload.get("source_name"),
                source_author=payload.get("source_author"),
                authors=payload.get("authors"),
                url=payload.get("url"),
                chunk_text=payload.get("chunk_text"),
                score=point.score,
                category=payload.get("category"),
                language=payload.get("language"),
                stars=payload.get("stars"),
                features=payload.get("features"),
                source_type=payload.get("source_type"),
            )
        )
        if len(results) >= limit:
            break

    logger.info(f"Returning {len(results)} unique title results for matching query '{query_text}'")

    # logger.info(f"results: {results}")
    return results
