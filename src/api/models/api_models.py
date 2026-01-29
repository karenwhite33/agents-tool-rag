from pydantic import BaseModel, Field


# -----------------------
# Core search result model
# -----------------------
class SearchResult(BaseModel):
    title: str = Field(default="", description="Title of the article/tool")
    feed_author: str | None = Field(default=None, description="Author of the article (deprecated)")
    feed_name: str | None = Field(default=None, description="Name of the feed/newsletter (deprecated)")
    article_author: list[str] | None = Field(default=None, description="List of article authors")
    # New fields for AI agent tools
    source_name: str | None = Field(default=None, description="Name of the source")
    source_author: str | None = Field(default=None, description="Author of the source")
    authors: list[str] | None = Field(default=None, description="List of authors")
    url: str | None = Field(default=None, description="URL of the article/tool")
    chunk_text: str | None = Field(default=None, description="Text content of the chunk")
    score: float = Field(default=0.0, description="Relevance score")
    # Tool-specific metadata
    category: str | None = Field(default=None, description="Category: Framework, Library, Platform, Tool")
    language: str | None = Field(default=None, description="Programming language")
    stars: int | None = Field(default=None, description="GitHub stars count")
    features: list[str] | None = Field(default=None, description="Key features")
    source_type: str | None = Field(default=None, description="Source type: rss_article, github_repo, documentation")


# -----------------------
# Unique titles request/response
# -----------------------
class UniqueTitleRequest(BaseModel):
    query_text: str = Field(
        default="", 
        max_length=2000,
        description="The user query text"
    )
    feed_author: str | None = Field(
        default=None, 
        max_length=200,
        description="Filter by author name (deprecated)"
    )
    feed_name: str | None = Field(
        default=None, 
        max_length=200,
        description="Filter by feed/newsletter name (deprecated)"
    )
    article_author: list[str] | None = Field(
        default=None, 
        max_length=10,
        description="List of article authors (max 10)"
    )
    title_keywords: str | None = Field(
        default=None, 
        max_length=500,
        description="Keywords or phrase to match in title"
    )
    # New filters for AI agent tools
    category: str | None = Field(
        default=None, 
        max_length=100,
        description="Filter by category"
    )
    language: str | None = Field(
        default=None, 
        max_length=50,
        description="Filter by programming language"
    )
    min_stars: int | None = Field(
        default=None, 
        ge=0,
        le=1000000,
        description="Filter by minimum GitHub stars"
    )
    source_type: str | None = Field(
        default=None, 
        max_length=50,
        description="Filter by source type"
    )
    limit: int = Field(
        default=5, 
        ge=1, 
        le=50,
        description="Number of results to return (1-50)"
    )


class UniqueTitleResponse(BaseModel):
    results: list[SearchResult] = Field(
        default_factory=list, description="List of unique title search results"
    )


# -----------------------
# Ask request model
# -----------------------
class AskRequest(BaseModel):
    query_text: str = Field(
        default="", 
        max_length=2000,
        description="The user query text"
    )
    feed_author: str | None = Field(
        default=None, 
        max_length=200,
        description="Filter by author name (deprecated)"
    )
    feed_name: str | None = Field(
        default=None, 
        max_length=200,
        description="Filter by feed/newsletter name (deprecated)"
    )
    article_author: list[str] | None = Field(
        default=None, 
        max_length=10,
        description="List of article authors (max 10)"
    )
    title_keywords: str | None = Field(
        default=None, 
        max_length=500,
        description="Keywords or phrase to match in title"
    )
    # New filters for AI agent tools
    category: str | None = Field(
        default=None, 
        max_length=100,
        description="Filter by category"
    )
    language: str | None = Field(
        default=None, 
        max_length=50,
        description="Filter by programming language"
    )
    min_stars: int | None = Field(
        default=None, 
        ge=0,
        le=1000000,
        description="Filter by minimum GitHub stars"
    )
    source_type: str | None = Field(
        default=None, 
        max_length=50,
        description="Filter by source type"
    )
    limit: int = Field(
        default=5, 
        ge=1, 
        le=50,
        description="Number of results to return (1-50)"
    )
    provider: str = Field(
        default="OpenRouter", 
        max_length=50,
        description="The provider to use for the query"
    )
    model: str | None = Field(
        default=None, 
        max_length=200,
        description="The specific model to use for the provider, if applicable"
    )


# -----------------------
# Ask response model
# -----------------------
class AskResponse(BaseModel):
    query: str = Field(default="", description="The original query text")
    provider: str = Field(default="", description="The LLM provider used for generation")
    answer: str = Field(default="", description="Generated answer from the LLM")
    sources: list[SearchResult] = Field(
        default_factory=list, description="List of source documents used in generation"
    )
    model: str | None = Field(
        default=None, description="The specific model used by the provider, if available"
    )
    finish_reason: str | None = Field(
        default=None, description="The reason why the generation finished, if available"
    )


# -----------------------
# Streaming "response" documentation
# -----------------------
class AskStreamingChunk(BaseModel):
    delta: str = Field(default="", description="Partial text generated by the LLM")


class AskStreamingResponse(BaseModel):
    query: str = Field(default="", description="The original query text")
    provider: str = Field(default="", description="The LLM provider used for generation")
    chunks: list[AskStreamingChunk] = Field(
        default_factory=list, description="Streamed chunks of generated text"
    )
