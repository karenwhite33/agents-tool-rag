import uuid
from uuid import UUID

from sqlalchemy import ARRAY, TIMESTAMP, BigInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.config import settings


class Base(DeclarativeBase):
    pass


class RSSArticle(Base):
    __tablename__ = "rss_articles"  # Hardcoded to avoid conflict with AIAgentTool

    # Primary internal ID
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)

    # External unique identifier
    uuid: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )

    # Article fields
    feed_name: Mapped[str] = mapped_column(String, nullable=False)
    feed_author: Mapped[str] = mapped_column(String, nullable=False)
    article_authors: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[str] = mapped_column(TIMESTAMP, nullable=False)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now(), nullable=False)


class AIAgentTool(Base):
    """Model for AI agent tools from multiple sources (RSS, GitHub, Documentation)."""

    __tablename__ = "ai_agent_tools"

    # Primary internal ID
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)

    # External unique identifier
    uuid: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )

    # Core fields (renamed from feed_* to source_*)
    source_name: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # e.g., "GitHub", "Dev.to", "LangChain Docs"
    source_author: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # e.g., "OpenAI", "LangChain Team"
    authors: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[str] = mapped_column(TIMESTAMP, nullable=False)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now(), nullable=False)

    # NEW fields for AI agent tools
    category: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )  # "Framework", "Library", "Platform", "Tool"
    language: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )  # "Python", "JavaScript", "TypeScript", etc.
    stars: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )  # GitHub stars
    features: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )  # Key features
    license_type: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # "MIT", "Apache-2.0", etc.
    source_type: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # "rss_article", "github_repo", "documentation"
