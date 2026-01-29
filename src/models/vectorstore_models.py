# src/models/qdrant_models.py
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


# -----------------------------
# Qdrant payload settings
# -----------------------------
class ArticleChunkPayload(BaseModel):
    feed_name: str = Field(default="", description="Name of the feed")
    feed_author: str = Field(default="", description="Author of the feed")
    article_authors: list[str] = Field(default_factory=list, description="Authors of the article")
    title: str = Field(default="", description="Title of the article")
    url: HttpUrl | str | None = Field(default=None, description="URL of the article")
    published_at: datetime | str = Field(
        default_factory=datetime.now, description="Publication date of the article"
    )
    created_at: datetime | str = Field(
        default_factory=datetime.now, description="Creation date of the article"
    )
    chunk_index: int = Field(default=0, description="Index of the article chunk")
    chunk_text: str | None = Field(default=None, description="Text content of the article chunk")


class ToolChunkPayload(BaseModel):
    """Payload for AI agent tool chunks in Qdrant vector store."""

    # Core fields (renamed from feed_* to source_*)
    source_name: str = Field(default="", description="Name of the source")
    source_author: str = Field(default="", description="Author of the source")
    authors: list[str] = Field(default_factory=list, description="Authors of the tool")
    title: str = Field(default="", description="Title of the tool")
    url: HttpUrl | str | None = Field(default=None, description="URL of the tool")
    published_at: datetime | str = Field(
        default_factory=datetime.now, description="Publication date of the tool"
    )
    created_at: datetime | str = Field(
        default_factory=datetime.now, description="Creation date of the tool"
    )
    chunk_index: int = Field(default=0, description="Index of the tool chunk")
    chunk_text: str | None = Field(default=None, description="Text content of the tool chunk")

    # New fields for filtering
    category: str | None = Field(
        default=None, description="Category: Framework, Library, Platform, Tool"
    )
    language: str | None = Field(
        default=None, description="Programming language: Python, JavaScript, etc."
    )
    stars: int | None = Field(default=None, description="GitHub stars count")
    features: list[str] | None = Field(default=None, description="Key features of the tool")
    source_type: str = Field(
        default="rss_article",
        description="Source type: rss_article, github_repo, documentation",
    )
