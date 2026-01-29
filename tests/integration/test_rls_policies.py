"""Integration tests for Row Level Security (RLS) policies.

This test suite verifies that RLS is properly enabled and configured
on the ai_agent_tools and rss_articles tables.
"""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError

from src.infrastructure.supabase.init_session import init_engine


class TestRLSConfiguration:
    """Test suite for RLS configuration."""

    @pytest.fixture(scope="class")
    def engine(self):
        """Create database engine for testing."""
        engine = init_engine()
        yield engine
        engine.dispose()

    def test_rls_enabled_on_ai_agent_tools(self, engine):
        """Test that RLS is enabled on ai_agent_tools table."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT relrowsecurity
                FROM pg_class
                WHERE relname = 'ai_agent_tools'
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                """
                )
            )
            row = result.fetchone()
            assert row is not None, "ai_agent_tools table not found"
            assert row[0] is True, "RLS is not enabled on ai_agent_tools table"

    def test_rls_enabled_on_rss_articles(self, engine):
        """Test that RLS is enabled on rss_articles table."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT relrowsecurity
                FROM pg_class
                WHERE relname = 'rss_articles'
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                """
                )
            )
            row = result.fetchone()
            assert row is not None, "rss_articles table not found"
            assert row[0] is True, "RLS is not enabled on rss_articles table"

    def test_ai_agent_tools_has_select_policy(self, engine):
        """Test that ai_agent_tools has a SELECT policy for public access."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT policyname, cmd
                FROM pg_policies
                WHERE tablename = 'ai_agent_tools'
                AND cmd = 'SELECT'
                """
                )
            )
            rows = result.fetchall()
            assert len(rows) > 0, "No SELECT policy found for ai_agent_tools"
            policy_names = [row[0] for row in rows]
            assert (
                "ai_agent_tools_select_policy" in policy_names
            ), "Expected SELECT policy not found"

    def test_ai_agent_tools_has_insert_policy(self, engine):
        """Test that ai_agent_tools has an INSERT policy."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT policyname, cmd
                FROM pg_policies
                WHERE tablename = 'ai_agent_tools'
                AND cmd = 'INSERT'
                """
                )
            )
            rows = result.fetchall()
            assert len(rows) > 0, "No INSERT policy found for ai_agent_tools"
            policy_names = [row[0] for row in rows]
            assert (
                "ai_agent_tools_insert_policy" in policy_names
            ), "Expected INSERT policy not found"

    def test_ai_agent_tools_has_update_policy(self, engine):
        """Test that ai_agent_tools has an UPDATE policy."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT policyname, cmd
                FROM pg_policies
                WHERE tablename = 'ai_agent_tools'
                AND cmd = 'UPDATE'
                """
                )
            )
            rows = result.fetchall()
            assert len(rows) > 0, "No UPDATE policy found for ai_agent_tools"
            policy_names = [row[0] for row in rows]
            assert (
                "ai_agent_tools_update_policy" in policy_names
            ), "Expected UPDATE policy not found"

    def test_ai_agent_tools_has_delete_policy(self, engine):
        """Test that ai_agent_tools has a DELETE policy."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT policyname, cmd
                FROM pg_policies
                WHERE tablename = 'ai_agent_tools'
                AND cmd = 'DELETE'
                """
                )
            )
            rows = result.fetchall()
            assert len(rows) > 0, "No DELETE policy found for ai_agent_tools"
            policy_names = [row[0] for row in rows]
            assert (
                "ai_agent_tools_delete_policy" in policy_names
            ), "Expected DELETE policy not found"

    def test_rss_articles_has_all_policies(self, engine):
        """Test that rss_articles has all 4 policies."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT COUNT(*)
                FROM pg_policies
                WHERE tablename = 'rss_articles'
                """
                )
            )
            count = result.fetchone()[0]
            assert count == 4, f"Expected 4 policies for rss_articles, found {count}"

    def test_ai_agent_tools_has_all_policies(self, engine):
        """Test that ai_agent_tools has all 4 policies."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT COUNT(*)
                FROM pg_policies
                WHERE tablename = 'ai_agent_tools'
                """
                )
            )
            count = result.fetchone()[0]
            assert count == 4, f"Expected 4 policies for ai_agent_tools, found {count}"

    def test_select_policy_is_for_public_role(self, engine):
        """Test that SELECT policy is accessible to public role."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT roles
                FROM pg_policies
                WHERE tablename = 'ai_agent_tools'
                AND policyname = 'ai_agent_tools_select_policy'
                """
                )
            )
            row = result.fetchone()
            assert row is not None, "SELECT policy not found"
            roles = row[0]
            # The roles array should contain 'public' or be {public}
            assert (
                "public" in str(roles).lower()
            ), f"SELECT policy should be for public role, got: {roles}"

    def test_insert_policy_is_for_authenticated_role(self, engine):
        """Test that INSERT policy requires authenticated role."""
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT roles
                FROM pg_policies
                WHERE tablename = 'ai_agent_tools'
                AND policyname = 'ai_agent_tools_insert_policy'
                """
                )
            )
            row = result.fetchone()
            assert row is not None, "INSERT policy not found"
            roles = row[0]
            # The roles array should contain 'authenticated'
            assert (
                "authenticated" in str(roles).lower()
            ), f"INSERT policy should be for authenticated role, got: {roles}"


class TestRLSEnforcement:
    """Test suite to verify RLS policy enforcement.
    
    Note: These tests assume you're using a service_role connection
    which bypasses RLS. For full RLS testing, you would need separate
    anon and authenticated connections.
    """

    @pytest.fixture(scope="class")
    def engine(self):
        """Create database engine for testing."""
        engine = init_engine()
        yield engine
        engine.dispose()

    def test_can_query_with_service_role(self, engine):
        """Test that service role can query tables (bypasses RLS)."""
        with engine.connect() as conn:
            # Should work with service role
            result = conn.execute(text("SELECT COUNT(*) FROM ai_agent_tools"))
            count = result.fetchone()[0]
            assert count >= 0, "Query should succeed with service role"

    def test_tables_exist(self, engine):
        """Test that both tables exist in the database."""
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "ai_agent_tools" in tables, "ai_agent_tools table not found"
        assert "rss_articles" in tables, "rss_articles table not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
