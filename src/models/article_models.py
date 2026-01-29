from pydantic import BaseModel, Field


# -----------------------------
# Feed settings
# -----------------------------
class FeedItem(BaseModel):
    name: str = Field(default="", description="Name of the feed")
    author: str = Field(default="", description="Author of the feed")
    url: str = Field(default="", description="URL of the feed")


# -----------------------------
# Article settings
# -----------------------------
class ArticleItem(BaseModel):
    feed_name: str = Field(default="", description="Name of the feed")
    feed_author: str = Field(default="", description="Author of the feed")
    title: str = Field(default="", description="Title of the article")
    url: str = Field(default="", description="URL of the article")
    content: str = Field(default="", description="Content of the article")
    article_authors: list[str] = Field(default_factory=list, description="Authors of the article")
    published_at: str | None = Field(default=None, description="Publication date of the article")
    # cover_image: str | None = None


# -----------------------------
# AI Agent Tool settings
# -----------------------------
class ToolItem(BaseModel):
    """Model for AI agent tools from multiple sources (RSS, GitHub, Documentation)."""

    # Core fields (renamed from feed_* to source_*)
    source_name: str = Field(default="", description="Name of the source")
    source_author: str = Field(default="", description="Author of the source")
    title: str = Field(default="", description="Title of the tool")
    url: str = Field(default="", description="URL of the tool")
    content: str = Field(default="", description="Content/description of the tool")
    authors: list[str] = Field(default_factory=list, description="Authors of the tool")
    published_at: str | None = Field(default=None, description="Publication date of the tool")

    # New fields for AI agent tools
    category: str | None = Field(
        default=None, description="Category: Framework, Library, Platform, Tool"
    )
    language: str | None = Field(
        default=None, description="Programming language: Python, JavaScript, TypeScript, etc."
    )
    stars: int | None = Field(default=None, description="GitHub stars count")
    features: list[str] | None = Field(default=None, description="Key features of the tool")
    license_type: str | None = Field(default=None, description="License type: MIT, Apache-2.0, etc.")
    source_type: str = Field(
        default="rss_article",
        description="Source type: rss_article, github_repo, documentation",
    )


# -----------------------------
# Documentation Site settings
# -----------------------------
class DocSite(BaseModel):
    """Configuration for documentation sites to scrape."""

    name: str = Field(default="", description="Name of the documentation site")
    url: str = Field(default="", description="URL of the documentation site")
    base_url: str = Field(default="", description="Base URL for relative links")
