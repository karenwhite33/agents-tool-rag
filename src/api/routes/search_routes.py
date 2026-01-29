import asyncio

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.models.api_models import (
    AskRequest,
    AskResponse,
    AskStreamingResponse,
    SearchResult,
    UniqueTitleRequest,
    UniqueTitleResponse,
)
from src.api.services.generation_service import generate_answer, get_streaming_function
from src.api.services.search_service import query_unique_titles, query_with_filters
from src.utils.logger_util import setup_logging

logger = setup_logging()

router = APIRouter()

# Rate limiter instance (will be initialized in main.py)
_limiter: Limiter | None = None


def set_limiter(limiter_instance: Limiter) -> None:
    """Set the rate limiter instance.
    
    Args:
        limiter_instance (Limiter): The rate limiter instance from app.state.
    """
    global _limiter
    _limiter = limiter_instance


def rate_limit_decorator(limit_str: str):
    """Create a rate limit decorator that works conditionally.
    
    Args:
        limit_str (str): Rate limit string (e.g., "30/minute").
        
    Returns:
        Decorator function.
    """
    def decorator(func):
        if _limiter:
            return _limiter.limit(limit_str)(func)
        return func
    return decorator


@router.post("/unique-titles", response_model=UniqueTitleResponse)
@rate_limit_decorator("60/minute")  # Rate limit: 60/min
async def search_unique(request: Request, params: UniqueTitleRequest):
    """Returns unique article/tool titles based on a query and optional filters.

    Deduplicates results by article/tool title.

    Args:
        request: FastAPI request object.
        params: UniqueTitleRequest with search parameters.

    Returns:
        UniqueTitleResponse: List of unique titles.

    """
    results = await query_unique_titles(
        request=request,
        query_text=params.query_text,
        feed_author=params.feed_author,
        feed_name=params.feed_name,
        title_keywords=params.title_keywords,
        category=params.category,
        language=params.language,
        min_stars=params.min_stars,
        source_type=params.source_type,
        limit=params.limit,
    )
    return {"results": results}


@router.post("/ask", response_model=AskResponse)
@rate_limit_decorator("30/minute")  # Rate limit: 30/min (more expensive)
async def ask_with_generation(request: Request, ask: AskRequest):
    """Non-streaming question-answering endpoint using vector search and LLM.

    Workflow:
        1. Retrieve relevant documents (possibly duplicate titles for richer context).
        2. Generate an answer with the selected LLM provider.

    Args:
        request: FastAPI request object.
        ask: AskRequest with query, provider, and limit.

    Returns:
        AskResponse: Generated answer and source documents.

    """
    # Step 1: Retrieve relevant documents with filters
    results: list[SearchResult] = await query_with_filters(
        request,
        query_text=ask.query_text,
        feed_author=ask.feed_author,
        feed_name=ask.feed_name,
        title_keywords=ask.title_keywords,
        category=ask.category,
        language=ask.language,
        min_stars=ask.min_stars,
        source_type=ask.source_type,
        limit=ask.limit,
    )

    # Step 2: Generate an answer with error handling
    try:
        answer_data = await generate_answer(
            query=ask.query_text, contexts=results, provider=ask.provider, selected_model=ask.model
        )
    except ValueError as e:
        # Security: Log the attempt but don't expose details
        logger.warning(f"Invalid query rejected from {request.client.host if request.client else 'unknown'}: {str(e)[:100]}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_query",
                "message": "Your query contains invalid characters or patterns. Please rephrase your question."
            }
        )

    return AskResponse(
        query=ask.query_text,
        provider=ask.provider,
        answer=answer_data["answer"],
        sources=results,
        model=answer_data.get("model", None),
        finish_reason=answer_data.get("finish_reason", None),
    )


@router.post("/ask/stream", response_model=AskStreamingResponse)
@rate_limit_decorator("30/minute")  # Rate limit: 30/min (more expensive)
async def ask_with_generation_stream(request: Request, ask: AskRequest):
    """Streaming question-answering endpoint using vector search and LLM.

    Workflow:
        1. Retrieve relevant documents (possibly duplicate titles for richer context).
        2. Stream generated answer with the selected LLM provider.

    Args:
        request: FastAPI request object.
        ask: AskRequest with query, provider, and limit.

    Returns:
        StreamingResponse: Yields text chunks as plain text.

    """
    # Step 1: Retrieve relevant documents with filters
    results: list[SearchResult] = await query_with_filters(
        request,
        query_text=ask.query_text,
        feed_author=ask.feed_author,
        feed_name=ask.feed_name,
        title_keywords=ask.title_keywords,
        category=ask.category,
        language=ask.language,
        min_stars=ask.min_stars,
        source_type=ask.source_type,
        limit=ask.limit,
    )

    # Step 2: Get the streaming generator with error handling
    try:
        stream_func = get_streaming_function(
            provider=ask.provider, query=ask.query_text, contexts=results, selected_model=ask.model
        )
    except ValueError as e:
        # Security: Log the attempt but don't expose details
        logger.warning(f"Invalid query rejected from {request.client.host if request.client else 'unknown'}: {str(e)[:100]}")
        # For streaming, we need to yield an error message
        async def error_stream():
            yield "__error__Invalid query. Please rephrase your question."
        return StreamingResponse(error_stream(), media_type="text/plain")

    # Step 3: Wrap streaming generator
    async def stream_generator():
        try:
            async for delta in stream_func():
                yield delta
                await asyncio.sleep(0)  # allow event loop to handle other tasks
        except ValueError:
            # If error occurs during streaming, yield error marker
            yield "__error__Invalid query. Please rephrase your question."

    return StreamingResponse(stream_generator(), media_type="text/plain")
