# Changelog

## 2.0.1 (Security Update)

Released on January 14, 2026.

### 🔒 Security Fix: Row Level Security (RLS)

**Critical security update to fix RLS vulnerability in Supabase tables.**

#### Fixed

- **RLS Disabled on Public Tables**: Enabled Row Level Security on `ai_agent_tools` and `rss_articles` tables
- **Missing Security Policies**: Created comprehensive RLS policies to control data access
  - Public read access (SELECT) for API endpoints
  - Authenticated-only write access (INSERT, UPDATE, DELETE)

#### Added

- **Migration Script**: `src/infrastructure/supabase/enable_rls.py` to enable RLS on existing databases
- **RLS Tests**: Test suite at `tests/integration/test_rls_policies.py`
- **Makefile Commands**: `make supabase-enable-rls` and `make supabase-test-rls`

#### Changed

- **Database Creation**: `src/infrastructure/supabase/create_db.py` now enables RLS automatically
- **README**: Added security section with RLS setup instructions

#### Impact

- ✅ Prevents unauthorized data access
- ✅ Restricts write operations to authenticated users only
- ✅ Maintains API functionality (read access remains public)
- ✅ No breaking changes to existing code

#### Upgrade Instructions

```bash
make supabase-enable-rls
```

---

## 2.0.0

Released on January 13, 2026.

### 🚀 Major Transformation: AI Agent Tools Search Engine

Completely transformed the project from an RSS newsletter search to a comprehensive AI Agent Tools search engine.

#### Added

- **GitHub Integration**: Fetch AI agent repositories with stars, language, license, and README content
- **Documentation Scraping**: Scrape official docs from LangChain, CrewAI, LlamaIndex, and more
- **New Database Model**: `AIAgentTool` table with rich metadata (category, language, stars, features, source_type)
- **Advanced Filters**: Category, language, GitHub stars, and source type filtering
- **Enhanced UI**: Colored badges, metadata display, and new filter controls
- **Unified Ingestion Flow**: Single flow to ingest from RSS, GitHub, and documentation sources
- **Comprehensive Documentation**: Migration guide, data sources guide, environment variables guide

#### Changed

- **Project Name**: `rss-newsletters-search` → `agents-tool-rag`
- **UI Title**: "RSS Articles LLM Engine" → "AI Agent Tools Search Engine"
- **RSS Feeds**: Updated to AI/ML-focused feeds (LangChain, Hugging Face, etc.)
- **Search API**: Extended with new filter parameters
- **Vector Store Payloads**: Added category, language, stars, features fields

#### Technical Improvements

- GitHub API integration with rate limit handling
- Sitemap-based documentation scraping
- Category detection from topics/tags
- Language detection from content
- Backward compatibility with legacy endpoints

---

## 1.0.0

Released on September 30, 2025.

### Added

- Initial release of the RSS Articles Search Engine
- Utilizes Prefect for workflow orchestration and scheduling
- Fetches articles from RSS newsletters and feeds
- Processes and cleans article content and metadata and ingests into a Supabase SQL table
- Ingest articles from the Supabase SQL table into a Qdrant vector store collection
- Implements a backend API using FastAPI to handle search queries and serve results
- Deploys the application on Google Cloud Run for scalability.
- Provides a Gradio-based user interface for searching and displaying articles
- Includes CI/CD pipelines for automated testing and deployment.
