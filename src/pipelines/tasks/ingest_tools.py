from prefect import task
from prefect.cache_policies import NO_CACHE
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.config import settings
from src.infrastructure.supabase.init_session import init_session
from src.models.article_models import FeedItem, ToolItem
from src.models.sql_models import AIAgentTool
from src.utils.logger_util import setup_logging


@task(
    task_run_name="batch_ingest_tools-{feed.name}",
    description="Ingest AI agent tools in batches.",
    retries=2,
    retry_delay_seconds=120,
    cache_policy=NO_CACHE,
)
def ingest_tools(
    fetched_tools: list[ToolItem],
    feed: FeedItem,
    tool_model: type[AIAgentTool],
    engine: Engine,
) -> None:
    """Ingest tools fetched from RSS or other sources.

    Tools are inserted in batches to optimize database writes. Errors during
    ingestion of individual batches are logged but do not stop subsequent batches.

    Args:
        fetched_tools: List of ToolItem objects to ingest.
        feed: The FeedItem representing the source feed.
        tool_model: The SQLAlchemy model class for tools.
        engine: SQLAlchemy Engine for database connection.

    Raises:
        RuntimeError: If ingestion completes with errors.
    """

    logger = setup_logging()
    rss = settings.rss
    errors = []
    batch: list[ToolItem] = []

    session: Session = init_session(engine)

    try:
        for i, tool in enumerate(fetched_tools, start=1):
            batch.append(tool)

            if len(batch) >= rss.batch_size:
                batch_num = i // rss.batch_size
                try:
                    _persist_batch(session, batch, tool_model)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to ingest batch {batch_num} for feed '{feed.name}': {e}")
                    errors.append(f"Batch {batch_num}")
                else:
                    logger.info(
                        f"🔁 Ingested batch {batch_num} with {len(batch)} tools "
                        f"for feed '{feed.name}'"
                    )
                batch = []

        # leftovers
        if batch:
            try:
                _persist_batch(session, batch, tool_model)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to ingest final batch for feed '{feed.name}': {e}")
                errors.append("Final batch")
            else:
                logger.info(
                    f"👉 Ingested final batch of {len(batch)} tools for feed '{feed.name}'"
                )

        if errors:
            raise RuntimeError(f"Ingestion completed with errors: {errors}")

    except Exception as e:
        logger.error(f"Unexpected error in ingest_tools for feed '{feed.name}': {e}")
        raise
    finally:
        session.close()
        logger.info(f"Database session closed for feed '{feed.name}'")


def _persist_batch(
    session: Session,
    batch: list[ToolItem],
    tool_model: type[AIAgentTool],
) -> None:
    """Helper to bulk insert a batch of ToolItems with duplicate handling.
    
    Uses PostgreSQL's ON CONFLICT DO NOTHING to skip duplicates based on URL.
    This prevents the entire batch from failing if any duplicate URLs exist.
    """
    values = [
        {
            "source_name": tool.source_name,
            "source_author": tool.source_author,
            "title": tool.title,
            "url": tool.url,
            "content": tool.content,
            "authors": tool.authors,
            "published_at": tool.published_at,
            "category": tool.category,
            "language": tool.language,
            "stars": tool.stars,
            "features": tool.features,
            "license_type": tool.license_type,
            "source_type": tool.source_type,
        }
        for tool in batch
    ]
    
    # Use PostgreSQL's INSERT ... ON CONFLICT DO NOTHING
    # to silently skip duplicates based on the unique URL constraint
    stmt = insert(tool_model).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
    session.execute(stmt)
