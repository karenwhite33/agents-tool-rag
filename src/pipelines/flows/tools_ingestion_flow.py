"""Unified ingestion flow for AI Agent Tools from multiple sources."""

from prefect import flow

from src.config import settings
from src.infrastructure.supabase.init_session import init_engine
from src.models.sql_models import AIAgentTool
from src.pipelines.tasks.fetch_docs import fetch_documentation, load_doc_sites
from src.pipelines.tasks.fetch_github import fetch_github_repos
from src.pipelines.tasks.fetch_tools import fetch_tools_from_rss
from src.pipelines.tasks.ingest_tools import ingest_tools
from src.utils.logger_util import setup_logging

logger = setup_logging()


@flow(
    name="ai_tools_ingest_flow",
    description="Unified flow to ingest AI agent tools from RSS, GitHub, and Documentation sources",
    log_prints=True,
)
def ai_tools_ingest_flow(
    enable_rss: bool = True,
    enable_github: bool = True,
    enable_docs: bool = True,
) -> None:
    """Ingest AI agent tools from multiple sources.

    Args:
        enable_rss (bool): Enable RSS feed ingestion. Defaults to True.
        enable_github (bool): Enable GitHub repository ingestion. Defaults to True.
        enable_docs (bool): Enable documentation site ingestion. Defaults to True.

    Raises:
        Exception: If any critical ingestion step fails.
    """
    logger.info("🚀 Starting AI Agent Tools ingestion flow...")
    engine = init_engine()
    all_tools = []

    try:
        # 1. Fetch RSS articles
        if enable_rss:
            logger.info("📰 Fetching tools from RSS feeds...")
            for feed in settings.rss.feeds:
                try:
                    rss_items = fetch_tools_from_rss(
                        feed=feed, engine=engine, tool_model=AIAgentTool
                    )
                    all_tools.extend(rss_items)
                    logger.info(f"✓ Fetched {len(rss_items)} tools from {feed.name}")
                except Exception as e:
                    logger.error(f"✗ Failed to fetch from {feed.name}: {e}")
                    continue

        # 2. Fetch GitHub repos
        if enable_github:
            logger.info("📦 Fetching tools from GitHub...")
            try:
                github_items = fetch_github_repos(engine=engine)
                all_tools.extend(github_items)
                logger.info(f"✓ Fetched {len(github_items)} repos from GitHub")
            except Exception as e:
                logger.error(f"✗ Failed to fetch from GitHub: {e}")

        # 3. Fetch documentation
        if enable_docs:
            logger.info("📚 Fetching tools from documentation sites...")
            doc_sites = load_doc_sites("src/configs/doc_sites.yaml")
            for doc_site in doc_sites:
                try:
                    docs_items = fetch_documentation(
                        doc_site=doc_site, engine=engine, max_pages=20
                    )
                    all_tools.extend(docs_items)
                    logger.info(f"✓ Fetched {len(docs_items)} pages from {doc_site.name}")
                except Exception as e:
                    logger.error(f"✗ Failed to fetch from {doc_site.name}: {e}")
                    continue

        # 4. Ingest all tools to database
        if all_tools:
            logger.info(f"💾 Ingesting {len(all_tools)} total tools to database...")
            # Group tools by source for better logging
            from src.models.article_models import FeedItem

            dummy_feed = FeedItem(name="Combined Sources", author="Various", url="")
            ingest_tools(
                fetched_tools=all_tools,
                feed=dummy_feed,
                tool_model=AIAgentTool,
                engine=engine,
            )
            logger.info(f"✅ Successfully ingested {len(all_tools)} tools!")
        else:
            logger.warning("⚠️ No new tools found to ingest.")

    except Exception as e:
        logger.error(f"❌ Critical error in AI Tools ingestion flow: {e}")
        raise
    finally:
        engine.dispose()
        logger.info("🏁 AI Agent Tools ingestion flow completed.")


if __name__ == "__main__":
    # Run the flow locally for testing
    ai_tools_ingest_flow(enable_rss=True, enable_github=True, enable_docs=True)
