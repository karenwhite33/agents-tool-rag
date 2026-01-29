from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from src.infrastructure.supabase.init_session import init_engine
from src.models.sql_models import AIAgentTool, Base, RSSArticle
from src.utils.logger_util import setup_logging

logger = setup_logging()


def enable_rls_and_policies(engine) -> None:
    """Enable Row Level Security (RLS) and create policies for tables.

    This function enables RLS on both ai_agent_tools and rss_articles tables
    and creates policies that:
    - Allow public SELECT (read) access for the API
    - Allow INSERT, UPDATE, DELETE for authenticated users only

    Args:
        engine: SQLAlchemy engine instance

    Returns:
        None

    Raises:
        SQLAlchemyError: If an error occurs during RLS setup
    """
    try:
        with engine.begin() as conn:
            # Enable RLS on ai_agent_tools table
            logger.info("Enabling RLS on ai_agent_tools table...")
            conn.execute(text("ALTER TABLE public.ai_agent_tools ENABLE ROW LEVEL SECURITY;"))

            # Drop existing policies if they exist (for idempotency)
            conn.execute(
                text(
                    "DROP POLICY IF EXISTS ai_agent_tools_select_policy ON public.ai_agent_tools;"
                )
            )
            conn.execute(
                text(
                    "DROP POLICY IF EXISTS ai_agent_tools_insert_policy ON public.ai_agent_tools;"
                )
            )
            conn.execute(
                text(
                    "DROP POLICY IF EXISTS ai_agent_tools_update_policy ON public.ai_agent_tools;"
                )
            )
            conn.execute(
                text(
                    "DROP POLICY IF EXISTS ai_agent_tools_delete_policy ON public.ai_agent_tools;"
                )
            )

            # Create policy for public SELECT access
            conn.execute(
                text(
                    """
                CREATE POLICY ai_agent_tools_select_policy
                ON public.ai_agent_tools
                FOR SELECT
                TO public
                USING (true);
                """
                )
            )
            logger.info("Created SELECT policy for ai_agent_tools (public read access)")

            # Create policy for authenticated INSERT
            conn.execute(
                text(
                    """
                CREATE POLICY ai_agent_tools_insert_policy
                ON public.ai_agent_tools
                FOR INSERT
                TO authenticated
                WITH CHECK (true);
                """
                )
            )
            logger.info("Created INSERT policy for ai_agent_tools (authenticated only)")

            # Create policy for authenticated UPDATE
            conn.execute(
                text(
                    """
                CREATE POLICY ai_agent_tools_update_policy
                ON public.ai_agent_tools
                FOR UPDATE
                TO authenticated
                USING (true)
                WITH CHECK (true);
                """
                )
            )
            logger.info("Created UPDATE policy for ai_agent_tools (authenticated only)")

            # Create policy for authenticated DELETE
            conn.execute(
                text(
                    """
                CREATE POLICY ai_agent_tools_delete_policy
                ON public.ai_agent_tools
                FOR DELETE
                TO authenticated
                USING (true);
                """
                )
            )
            logger.info("Created DELETE policy for ai_agent_tools (authenticated only)")

            # Enable RLS on rss_articles table
            logger.info("Enabling RLS on rss_articles table...")
            conn.execute(text("ALTER TABLE public.rss_articles ENABLE ROW LEVEL SECURITY;"))

            # Drop existing policies if they exist (for idempotency)
            conn.execute(
                text(
                    "DROP POLICY IF EXISTS rss_articles_select_policy ON public.rss_articles;"
                )
            )
            conn.execute(
                text(
                    "DROP POLICY IF EXISTS rss_articles_insert_policy ON public.rss_articles;"
                )
            )
            conn.execute(
                text(
                    "DROP POLICY IF EXISTS rss_articles_update_policy ON public.rss_articles;"
                )
            )
            conn.execute(
                text(
                    "DROP POLICY IF EXISTS rss_articles_delete_policy ON public.rss_articles;"
                )
            )

            # Create policy for public SELECT access
            conn.execute(
                text(
                    """
                CREATE POLICY rss_articles_select_policy
                ON public.rss_articles
                FOR SELECT
                TO public
                USING (true);
                """
                )
            )
            logger.info("Created SELECT policy for rss_articles (public read access)")

            # Create policy for authenticated INSERT
            conn.execute(
                text(
                    """
                CREATE POLICY rss_articles_insert_policy
                ON public.rss_articles
                FOR INSERT
                TO authenticated
                WITH CHECK (true);
                """
                )
            )
            logger.info("Created INSERT policy for rss_articles (authenticated only)")

            # Create policy for authenticated UPDATE
            conn.execute(
                text(
                    """
                CREATE POLICY rss_articles_update_policy
                ON public.rss_articles
                FOR UPDATE
                TO authenticated
                USING (true)
                WITH CHECK (true);
                """
                )
            )
            logger.info("Created UPDATE policy for rss_articles (authenticated only)")

            # Create policy for authenticated DELETE
            conn.execute(
                text(
                    """
                CREATE POLICY rss_articles_delete_policy
                ON public.rss_articles
                FOR DELETE
                TO authenticated
                USING (true);
                """
                )
            )
            logger.info("Created DELETE policy for rss_articles (authenticated only)")

            logger.info("RLS and policies configured successfully for all tables")

    except SQLAlchemyError as e:
        logger.error(f"Error setting up RLS and policies: {e}")
        raise


def create_table() -> None:
    """Create the AIAgentTool and RSSArticle tables in the Supabase Postgres database.

    This function initializes a SQLAlchemy engine, checks if the tables exist,
    and creates them if necessary. Both tables are created for backward compatibility.
    After table creation, it enables Row Level Security (RLS) and creates appropriate
    policies to secure the tables.

    The engine is properly disposed of after the operation to prevent resource leaks.
    Errors during table creation are logged and handled gracefully.

    Args:
        None

    Returns:
        None

    Raises:
        SQLAlchemyError: If an error occurs during database operations (e.g., connection issues).
        Exception: For unexpected errors during table creation or inspection.

    """
    # Initialize the SQLAlchemy engine
    engine = init_engine()
    try:
        # Create an inspector to check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Check both tables
        ai_agent_table = AIAgentTool.__tablename__
        rss_table = RSSArticle.__tablename__

        tables_to_create = []
        if ai_agent_table not in existing_tables:
            tables_to_create.append(ai_agent_table)
        else:
            logger.info(f"Table '{ai_agent_table}' already exists.")

        if rss_table not in existing_tables:
            tables_to_create.append(rss_table)
        else:
            logger.info(f"Table '{rss_table}' already exists.")

        if tables_to_create:
            logger.info(f"Creating tables: {', '.join(tables_to_create)}")
            # Create all tables defined in Base.metadata
            Base.metadata.create_all(bind=engine)
            logger.info(f"Tables created successfully: {', '.join(tables_to_create)}")
        else:
            logger.info("All tables already exist. No action needed.")

        # Enable RLS and create policies for all tables
        logger.info("Setting up Row Level Security (RLS) and policies...")
        enable_rls_and_policies(engine)

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error creating tables: {e}")
        raise SQLAlchemyError("Failed to create tables") from e
    except Exception as e:
        logger.error(f"Unexpected error creating tables: {e}")
        raise
    finally:
        # Dispose of the engine to release connections
        engine.dispose()
        logger.info("Database engine disposed.")


if __name__ == "__main__":
    create_table()
