"""Rate limiting middleware for FastAPI."""

import os

from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.utils.logger_util import setup_logging

logger = setup_logging()

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default: 100 requests per minute per IP
    storage_uri="memory://",  # In-memory storage (use Redis for production)
)

# Rate limit configuration from environment
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

# Apply stricter limits for expensive endpoints
def get_rate_limit_for_endpoint(endpoint: str) -> str:
    """Get rate limit string based on endpoint.
    
    Args:
        endpoint (str): The endpoint path.
        
    Returns:
        str: Rate limit string (e.g., "30/minute").
    """
    # LLM endpoints are more expensive - stricter limits
    if "/ask" in endpoint or "/stream" in endpoint:
        return f"{RATE_LIMIT_PER_MINUTE // 2}/minute"  # Half the normal rate
    
    # Search endpoints are less expensive
    return f"{RATE_LIMIT_PER_MINUTE}/minute"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors.
    
    Args:
        request (Request): The FastAPI request.
        exc (RateLimitExceeded): The rate limit exception.
        
    Returns:
        HTTPException: HTTP 429 response.
    """
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)} on {request.url.path}")
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": int(exc.retry_after) if hasattr(exc, 'retry_after') else 60
        }
    )
