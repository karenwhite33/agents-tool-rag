import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from prefect import task
from prefect.cache_policies import NO_CACHE
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.infrastructure.supabase.init_session import init_session
from src.models.article_models import FeedItem, ToolItem
from src.models.sql_models import AIAgentTool
from src.utils.logger_util import setup_logging


@task(
    task_run_name="fetch_tools_from_rss-{feed.name}",
    description="Fetch RSS entries and convert them to ToolItems for AI agent tools.",
    retries=2,
    retry_delay_seconds=120,
    cache_policy=NO_CACHE,
)
def fetch_tools_from_rss(
    feed: FeedItem,
    engine: Engine,
    tool_model: type[AIAgentTool] = AIAgentTool,
) -> list[ToolItem]:
    """Fetch RSS items from a feed and convert them to ToolItem objects.

    Each task uses its own SQLAlchemy session. Tools already stored in the database
    or with empty links/content are skipped. Errors during parsing individual items
    are logged but do not stop processing.

    Args:
        feed (FeedItem): Metadata for the feed (name, author, URL).
        engine (Engine): SQLAlchemy engine for database connection.
        tool_model (type[AIAgentTool], optional): Model used to check for existing tools.
            Defaults to AIAgentTool.

    Returns:
        list[ToolItem]: List of new ToolItem objects ready for parsing/ingestion.

    Raises:
        RuntimeError: If the RSS fetch fails.
        Exception: For unexpected errors during execution.
    """

    logger = setup_logging()
    session: Session = init_session(engine)
    items: list[ToolItem] = []

    try:
        try:
            response = requests.get(feed.url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch feed '{feed.name}': {e}")
            raise RuntimeError(f"RSS fetch failed for feed '{feed.name}'") from e

        soup = BeautifulSoup(response.content, "xml")
        rss_items = soup.find_all("item")

        for _, item in enumerate(rss_items):
            try:
                link = item.find("link").get_text(strip=True) if item.find("link") else ""  # type: ignore
                if not link or session.query(tool_model).filter_by(url=link).first():
                    logger.info(
                        f"Skipping already stored or empty-link tool for feed '{feed.name}'"
                    )
                    continue

                title = (
                    item.find("title").get_text(strip=True) if item.find("title") else "Untitled"  # type: ignore
                )

                # Prefer full text in <content:encoded>
                content_elem = item.find("content:encoded") or item.find("description")  # type: ignore
                raw_html = content_elem.get_text() if content_elem else ""
                content_md = ""

                # Skip if article contains a self-referencing "Read more" link
                if raw_html:
                    try:
                        html_soup = BeautifulSoup(raw_html, "html.parser")
                        for a in html_soup.find_all("a", href=True):
                            if (
                                a["href"].strip() == link  # type: ignore
                                and "read more" in a.get_text(strip=True).lower()
                            ):
                                logger.info(f"Paywalled/truncated article skipped: '{title}'")
                                raise StopIteration  # skip this item
                    except StopIteration:
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to inspect links for '{title}': {e}")

                if raw_html:
                    try:
                        content_md = md(
                            raw_html,
                            strip=["script", "style"],
                            heading_style="ATX",
                            bullets="*",
                            autolinks=True,
                        )
                        content_md = "\n".join(
                            line.strip() for line in content_md.splitlines() if line.strip()
                        )
                    except Exception as e:
                        logger.warning(f"Markdown conversion failed for '{title}': {e}")
                        content_md = raw_html

                if not content_md:
                    logger.warning(f"Skipping tool '{title}' with empty content")
                    continue

                author_elem = item.find("creator") or item.find("dc:creator")  # type: ignore
                author = author_elem.get_text(strip=True) if author_elem else feed.author

                pub_date_elem = item.find("pubDate")  # type: ignore
                pub_date_str = pub_date_elem.get_text(strip=True) if pub_date_elem else None

                # Extract category from tags/keywords if available
                category = None
                categories = item.find_all("category")  # type: ignore
                if categories:
                    # Map common tags to our categories
                    tags = [cat.get_text(strip=True).lower() for cat in categories]
                    if any(tag in tags for tag in ["framework", "library", "tool", "platform"]):
                        category = next(
                            (
                                tag.title()
                                for tag in tags
                                if tag in ["framework", "library", "tool", "platform"]
                            ),
                            None,
                        )

                # Extract language if mentioned in content (basic detection)
                language = None
                content_lower = content_md.lower()
                languages = ["python", "javascript", "typescript", "go", "rust", "java"]
                for lang in languages:
                    if lang in content_lower[:500]:  # Check first 500 chars
                        language = lang.title()
                        break

                tool_item = ToolItem(
                    source_name=feed.name,
                    source_author=feed.author,
                    title=title,
                    url=link,
                    content=content_md,
                    authors=[author] if author else [],
                    published_at=pub_date_str,
                    category=category,
                    language=language,
                    stars=None,  # Not available from RSS
                    features=None,  # Could extract from content in future
                    license_type=None,  # Not available from RSS
                    source_type="rss_article",
                )
                items.append(tool_item)

            except Exception as e:
                logger.error(f"Error processing RSS item for feed '{feed.name}': {e}")
                continue

        logger.info(f"Fetched {len(items)} new tools for feed '{feed.name}'")
        return items

    except Exception as e:
        logger.error(f"Unexpected error in fetch_tools_from_rss for feed '{feed.name}': {e}")
        raise
    finally:
        session.close()
        logger.info(f"Database session closed for feed '{feed.name}'")
