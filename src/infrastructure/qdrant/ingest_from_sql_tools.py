"""Ingest AI agent tools from SQL database to Qdrant vector store."""

import asyncio
import hashlib

from sqlalchemy.exc import OperationalError

from src.config import settings
from src.infrastructure.qdrant.qdrant_vectorstore import AsyncQdrantVectorStore
from src.infrastructure.supabase.init_session import init_engine, init_session
from src.models.sql_models import AIAgentTool
from src.models.vectorstore_models import ToolChunkPayload
from src.utils.logger_util import setup_logging
from src.utils.text_splitter import TextSplitter

logger = setup_logging()


async def ingest_tools_to_vectorstore():
    """Ingest AI agent tools from SQL database to Qdrant vector store.

    Fetches all tools from the ai_agent_tools table, chunks their content,
    generates embeddings, and uploads them to Qdrant. Only processes tools
    that are new or have been updated (based on created_at timestamp).

    Raises:
        Exception: If ingestion fails.
    """
    logger.info("🚀 Starting ingestion of AI agent tools to Qdrant...")

    # Initialize database and vector store
    engine = init_engine()
    session = init_session(engine)
    vectorstore = AsyncQdrantVectorStore()

    try:
        # Fetch all tools from database
        tools = session.query(AIAgentTool).all()
        logger.info(f"📚 Found {len(tools)} tools in database")

        if not tools:
            logger.warning("⚠️ No tools found in database. Run ingestion flow first.")
            return

        # Get existing URLs from Qdrant to check what's already ingested
        logger.info("🔍 Checking existing tools in Qdrant...")
        existing_urls = await vectorstore.get_existing_tool_urls()
        logger.info(f"📊 Found {len(existing_urls)} tools already in Qdrant")

        # Filter tools to process: new tools or tools that have been updated
        tools_to_process: list[AIAgentTool] = []
        tools_to_update: list[AIAgentTool] = []
        
        for tool in tools:
            tool_url = tool.url
            # Compute content hash to detect changes
            content_hash = hashlib.sha256(tool.content.encode()).hexdigest()[:16]
            tool_created_at = str(tool.created_at) if tool.created_at else ""
            
            if tool_url not in existing_urls:
                # New tool - needs to be processed
                tools_to_process.append(tool)
            else:
                # Tool exists - check if content changed by comparing hash stored in created_at
                # We store content_hash in the created_at comparison for now
                # (In a production system, you'd want a separate content_hash field)
                existing_hash = existing_urls.get(tool_url, "")
                if existing_hash != content_hash:
                    # Content changed - needs to be updated
                    tools_to_update.append(tool)
                    tools_to_process.append(tool)
        
        logger.info(
            f"📝 Processing plan: {len(tools_to_process)} tools to process "
            f"({len(tools_to_process) - len(tools_to_update)} new, {len(tools_to_update)} updated)"
        )
        
        if not tools_to_process:
            logger.info("✅ All tools are already up-to-date in Qdrant. Nothing to process.")
            return

        # Delete old chunks for updated tools
        if tools_to_update:
            logger.info(f"🗑️  Deleting old chunks for {len(tools_to_update)} updated tools...")
            for tool in tools_to_update:
                try:
                    deleted_count = await vectorstore.delete_chunks_by_url(tool.url)
                    logger.debug(f"Deleted {deleted_count} old chunks for {tool.url}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to delete old chunks for {tool.url}: {e}")
                    # Continue processing even if deletion fails

        # Initialize text splitter
        splitter = TextSplitter(
            chunk_size=settings.text_splitter.chunk_size,
            chunk_overlap=settings.text_splitter.chunk_overlap,
            separators=settings.text_splitter.separators,
        )

        # Process tools in batches
        batch_size = settings.qdrant.article_batch_size
        for i in range(0, len(tools_to_process), batch_size):
            batch = tools_to_process[i : i + batch_size]
            logger.info(
                f"🔄 Processing batch {i // batch_size + 1}/{(len(tools_to_process) + batch_size - 1) // batch_size}"
            )

            # Prepare payloads for this batch
            payloads: list[ToolChunkPayload] = []
            texts: list[str] = []

            for tool in batch:
                # Split tool content into chunks
                chunks = splitter.split_text(tool.content)

                for chunk_idx, chunk_text in enumerate(chunks):
                    payload = ToolChunkPayload(
                        source_name=tool.source_name,
                        source_author=tool.source_author,
                        authors=tool.authors,
                        title=tool.title,
                        url=tool.url,
                        published_at=str(tool.published_at),
                        created_at=str(tool.created_at),
                        chunk_index=chunk_idx,
                        chunk_text=chunk_text,
                        category=tool.category,
                        language=tool.language,
                        stars=tool.stars,
                        features=tool.features,
                        source_type=tool.source_type,
                    )
                    payloads.append(payload)
                    texts.append(chunk_text)

            if not texts:
                logger.warning(f"⚠️ No text chunks generated for batch {i // batch_size + 1}")
                continue

            # Generate embeddings and upload to Qdrant
            logger.info(f"🔢 Generating embeddings for {len(texts)} chunks...")
            dense_vectors = vectorstore.dense_vectors(texts)
            sparse_vectors = vectorstore.sparse_vectors(texts)

            logger.info(f"☁️ Uploading {len(payloads)} chunks to Qdrant...")
            await vectorstore.upsert_chunks(
                payloads=payloads,
                dense_vectors=dense_vectors,
                sparse_vectors=sparse_vectors,
            )

            logger.info(f"✅ Batch {i // batch_size + 1} completed")

        logger.info(
            f"🎉 Successfully processed {len(tools_to_process)} tools to Qdrant! "
            f"({len(tools_to_process) - len(tools_to_update)} new, {len(tools_to_update)} updated)"
        )

    except Exception as e:
        logger.error(f"❌ Failed to ingest tools to vector store: {e}")
        raise
    finally:
        # Close session gracefully, handling connection errors
        try:
            session.close()
        except OperationalError as e:
            # Connection was already closed by server (e.g., timeout)
            # This is not critical since ingestion completed successfully
            logger.warning(f"⚠️ Database connection already closed: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Error closing session: {e}")
        
        # Dispose engine
        try:
            engine.dispose()
        except Exception as e:
            logger.warning(f"⚠️ Error disposing engine: {e}")


if __name__ == "__main__":
    asyncio.run(ingest_tools_to_vectorstore())
