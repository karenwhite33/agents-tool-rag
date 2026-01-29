"""Enable Row Level Security (RLS) on existing Supabase tables.

This script enables RLS and creates security policies for the ai_agent_tools
and rss_articles tables. Run this script to fix RLS security issues.

Usage:
    python -m src.infrastructure.supabase.enable_rls
"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.infrastructure.supabase.init_session import init_engine
from src.utils.logger_util import setup_logging

logger = setup_logging()


def enable_rls_policies() -> None:
    """Enable RLS and create policies for existing tables.

    This function:
    1. Enables RLS on ai_agent_tools and rss_articles tables
    2. Creates policies for public read access
    3. Restricts write operations to authenticated users only

    Returns:
        None

    Raises:
        SQLAlchemyError: If an error occurs during RLS setup
    """
    engine = init_engine()

    try:
        with engine.begin() as conn:
            logger.info("=" * 80)
            logger.info("Starting RLS configuration for Supabase tables")
            logger.info("=" * 80)

            # ========================================
            # Configure ai_agent_tools table
            # ========================================
            logger.info("\n[1/2] Configuring ai_agent_tools table...")

            # Enable RLS
            logger.info("  → Enabling RLS on ai_agent_tools...")
            conn.execute(text("ALTER TABLE public.ai_agent_tools ENABLE ROW LEVEL SECURITY;"))

            # Drop existing policies (idempotent)
            logger.info("  → Dropping existing policies (if any)...")
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

            # Create SELECT policy (public read access)
            logger.info("  → Creating SELECT policy (public read access)...")
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

            # Create INSERT policy (authenticated only)
            logger.info("  → Creating INSERT policy (authenticated users only)...")
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

            # Create UPDATE policy (authenticated only)
            logger.info("  → Creating UPDATE policy (authenticated users only)...")
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

            # Create DELETE policy (authenticated only)
            logger.info("  → Creating DELETE policy (authenticated users only)...")
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

            logger.info("  ✓ ai_agent_tools table configured successfully")

            # ========================================
            # Configure rss_articles table
            # ========================================
            logger.info("\n[2/2] Configuring rss_articles table...")

            # Enable RLS
            logger.info("  → Enabling RLS on rss_articles...")
            conn.execute(text("ALTER TABLE public.rss_articles ENABLE ROW LEVEL SECURITY;"))

            # Drop existing policies (idempotent)
            logger.info("  → Dropping existing policies (if any)...")
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

            # Create SELECT policy (public read access)
            logger.info("  → Creating SELECT policy (public read access)...")
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

            # Create INSERT policy (authenticated only)
            logger.info("  → Creating INSERT policy (authenticated users only)...")
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

            # Create UPDATE policy (authenticated only)
            logger.info("  → Creating UPDATE policy (authenticated users only)...")
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

            # Create DELETE policy (authenticated only)
            logger.info("  → Creating DELETE policy (authenticated users only)...")
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

            logger.info("  ✓ rss_articles table configured successfully")

            # ========================================
            # Summary
            # ========================================
            logger.info("\n" + "=" * 80)
            logger.info("RLS CONFIGURATION COMPLETE")
            logger.info("=" * 80)
            logger.info("\nSecurity policies applied:")
            logger.info("  • ai_agent_tools:")
            logger.info("      - SELECT: Public (anyone can read)")
            logger.info("      - INSERT/UPDATE/DELETE: Authenticated users only")
            logger.info("  • rss_articles:")
            logger.info("      - SELECT: Public (anyone can read)")
            logger.info("      - INSERT/UPDATE/DELETE: Authenticated users only")
            logger.info("\nYour Supabase tables are now secured with Row Level Security!")
            logger.info("=" * 80)

    except SQLAlchemyError as e:
        logger.error(f"\n❌ Error setting up RLS and policies: {e}")
        logger.error("Please check your database connection and permissions.")
        raise
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        raise
    finally:
        engine.dispose()
        logger.info("\nDatabase engine disposed.")


if __name__ == "__main__":
    enable_rls_policies()
