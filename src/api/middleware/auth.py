"""Authentication middleware for FastAPI."""

import os
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from src.utils.logger_util import setup_logging

logger = setup_logging()

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Get API key from environment
REQUIRED_API_KEY = os.getenv("API_KEY", "")

# Whether authentication is required (set to "false" to disable)
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header)
) -> None:
    """Verify API key from request header.
    
    This function is used as a FastAPI dependency to protect routes.
    
    Args:
        request (Request): The FastAPI request.
        api_key (str | None): The API key from header.
        
    Raises:
        HTTPException: If API key is missing or invalid.
    """
    # If authentication is disabled, allow all requests
    if not AUTH_REQUIRED:
        return
    
    # If no API key is configured, allow all requests (development mode)
    if not REQUIRED_API_KEY:
        logger.warning("API_KEY not set in environment - allowing all requests (INSECURE)")
        return
    
    # Check if API key is provided
    if not api_key:
        logger.warning(f"Missing API key for request from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "API key required. Please provide X-API-Key header."
            }
        )
    
    # Verify API key
    if api_key != REQUIRED_API_KEY:
        logger.warning(f"Invalid API key attempt from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Invalid API key."
            }
        )
