# 🤖 AI Agent Tools Search Engine

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python version](https://img.shields.io/badge/python-3.12.8-blue.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<p align="center">
  <em>A comprehensive RAG-powered search engine for discovering and exploring AI agent frameworks, libraries, and tools from multiple sources</em>
</p>

---

## 📚 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Data Sources](#-data-sources)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Security](#-security)
- [Usage](#-usage)
- [API Reference](#-api-reference)
- [Development](#-development)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

---

## 🎯 Overview

The AI Agent Tools Search Engine aggregates, indexes, and provides semantic search capabilities across AI agent frameworks, libraries, and documentation from three primary sources:

1. **RSS Feeds** - Latest articles and tutorials from AI/ML blogs
2. **GitHub Repositories** - Popular AI agent frameworks with metadata (stars, language, features)
3. **Documentation Sites** - Official documentation from frameworks like LangChain, CrewAI, etc.

<img width="1293" height="987" alt="react_app" src="https://github.com/user-attachments/assets/b2bd75eb-c9b0-49c7-a683-f20c7354cebe" />

## 🏁 [Vercel Deploy](https://agents-tool-rag.vercel.app/) 

### Why Use This?

- **Unified Search**: Search across GitHub repos, articles, and documentation in one place
- **Rich Metadata**: Filter by category, language, GitHub stars, source type
- **RAG-Powered QA**: Ask questions and get answers with source citations
- **Real-time Updates**: Prefect flows keep data fresh
- **Production-Ready**: FastAPI backend, Gradio UI, deployed on Google Cloud Run

---

## ✨ Features

### Search Capabilities

- **Semantic Search**: Hybrid dense + sparse search using Qdrant
- **Advanced Filters**:
  - Category (Framework, Library, Platform, Tool)
  - Programming Language (Python, JavaScript, TypeScript, Go, Rust)
  - Source Type (GitHub repo, RSS article, Documentation)
  - Minimum GitHub Stars
- **Deduplication**: Smart deduplication by title or point ID

### RAG Question Answering

- **Multi-Provider LLM Support**: OpenAI, OpenRouter, HuggingFace
- **Streaming Responses**: Real-time answer generation
- **Source Attribution**: See which tools/articles informed the answer
- **Context-Aware**: Filters apply to retrieval for focused answers

### Data Ingestion

- **Automated Pipelines**: Prefect flows for scheduled ingestion
- **Multiple Sources**: RSS, GitHub API, web scraping for docs
- **Robust Error Handling**: Retries, logging, graceful failures
- **Incremental Updates**: Only ingests new content

---

## 🏗️ Architecture
<img width="1536" height="1024" alt="app_diagram" src="https://github.com/user-attachments/assets/29591fb2-c8ca-43b0-a7fd-af3f313e3337" />

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                            │
├──────────────┬──────────────────┬──────────────────────────┤
│  RSS Feeds   │   GitHub API     │  Documentation Sites     │
│  (Articles)  │   (Repositories) │  (Web Scraping)         │
└──────┬───────┴────────┬─────────┴──────────┬──────────────┘
       │                │                     │
       ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Prefect Ingestion Flows                         │
│   - fetch_tools_from_rss()                                  │
│   - fetch_github_repos()                                    │
│   - fetch_documentation()                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         PostgreSQL (Supabase) - ai_agent_tools table        │
│  - source_name, source_author, title, url, content         │
│  - category, language, stars, features, license            │
│  - source_type (rss_article / github_repo / documentation) │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         Text Chunking & Embedding Generation                │
│  - RecursiveTextSplitter (4000 chars, 200 overlap)        │
│  - Dense: BAAI/bge-base-en (768d)                          │
│  - Sparse: BM25 (Qdrant)                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         Qdrant Vector Store (Hybrid Search)                 │
│  - Dense vectors (semantic similarity)                      │
│  - Sparse vectors (keyword matching)                        │
│  - Payload indexes (category, language, stars, type)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI Backend                              │
│  - /search/unique-titles (search endpoint)                 │
│  - /search/ask (RAG QA, non-streaming)                     │
│  - /search/ask/stream (RAG QA, streaming)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               Gradio Web UI                                 │
│  - Search Tools: Filter by category, language, stars       │
│  - Ask AI: RAG-powered Q&A with sources                    │
│  - Real-time streaming responses                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Sources

### 1. RSS Feeds (Articles)

**Purpose**: Latest tutorials, guides, and news about AI agents

**Feeds Included**:
- LangChain Blog
- Hugging Face Blog
- Towards Data Science
- TechCrunch AI
- Various AI/ML newsletters

**Data Extracted**:
- Title, URL, content (markdownified)
- Author, publication date
- Category/language (inferred from tags)

### 2. GitHub Repositories

**Purpose**: Discover popular AI agent frameworks and libraries

**Search Query**: "AI agent framework" with stars >100

**Data Extracted**:
- Repo name, description, URL
- Stars, language, license, topics
- README content (first 10k chars)
- Owner/organization

**API**: GitHub REST API v3
- Rate limit: 5000 req/hr (authenticated)
- Requires `GITHUB__API_KEY`

### 3. Documentation Sites

**Purpose**: Official documentation for major frameworks

**Sites Scraped**:
- LangChain (https://python.langchain.com/docs/)
- CrewAI (https://docs.crewai.com/)
- LlamaIndex (https://docs.llamaindex.ai/)
- Hugging Face Transformers
- Semantic Kernel
- AutoGPT

**Data Extracted**:
- Page title, content (markdownified)
- Headings (extracted as features)
- URL, publication date

**Method**: Web scraping with BeautifulSoup
- Respects robots.txt
- Handles sitemap.xml when available
- Graceful fallback for different site structures

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12.8+
- PostgreSQL database (Supabase recommended)
- Qdrant vector store (cloud or local)
- GitHub Personal Access Token

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-agent-tools-search.git
cd ai-agent-tools-search

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file (copy from `.env.example` and fill in values). **Do not commit `.env` or real API keys**; see `SECURITY.md` for details.

```bash
# Database (Supabase)
SUPABASE_DB__HOST=your-supabase-host.supabase.co
SUPABASE_DB__NAME=postgres
SUPABASE_DB__USER=postgres
SUPABASE_DB__PASSWORD=your-password
SUPABASE_DB__PORT=6543

# Qdrant
QDRANT__URL=https://your-qdrant-cluster.qdrant.io
QDRANT__API_KEY=your-qdrant-api-key
QDRANT__COLLECTION_NAME=ai_agent_tools_collection

# GitHub API (Required)
GITHUB__API_KEY=ghp_your_github_token_here
GITHUB__SEARCH_QUERY="AI agent framework"
GITHUB__MIN_STARS=100
GITHUB__MAX_REPOS=50

# LLM Providers (Optional)
OPENAI__API_KEY=your-openai-key
OPENROUTER__API_KEY=your-openrouter-key
HUGGING_FACE__API_KEY=your-hf-key

# Observability (Optional)
OPIK__API_KEY=your-opik-key
```

### Create Database & Vector Store

```bash
# Create PostgreSQL table
python -m src.infrastructure.supabase.create_db

# Create Qdrant collection
python -m src.infrastructure.qdrant.create_collection
python -m src.infrastructure.qdrant.create_indexes
```

### Run Initial Ingestion

```bash
# Ingest from all sources (RSS + GitHub + Docs)
python -m src.pipelines.flows.tools_ingestion_flow

# Upload to Qdrant vector store
python -m src.infrastructure.qdrant.ingest_from_sql_tools
```

### Start the Application

**First time (or after pulling dependency changes):** install backend dependencies from the repo root:

```bash
uv sync
```

Then:

```bash
# Start FastAPI backend (Terminal 1) — use uv run so project deps (e.g. qdrant-client) are used
uv run uvicorn src.api.main:app --reload --port 8080

# Start Gradio UI (Terminal 2, optional)
uv run gradio-frontend/app.py

# Or start React frontend (Terminal 2)
cd frontend && npm install && npm run dev
```

Visit:
- React frontend: http://localhost:5173
- Gradio UI: http://localhost:7860
- API Docs: http://localhost:8080/docs

---

## ⚙️ Configuration

### RSS Feeds (`src/configs/feeds_rss.yaml`)

```yaml
feeds:
- name: "LangChain Blog"
  author: "LangChain Team"
  url: "https://blog.langchain.dev/feed/"
- name: "Hugging Face Blog"
  author: "Hugging Face Team"
  url: "https://huggingface.co/blog/feed.xml"
```

### Documentation Sites (`src/configs/doc_sites.yaml`)

```yaml
sites:
- name: "LangChain"
  url: "https://python.langchain.com/docs/"
  base_url: "https://python.langchain.com"
  category: "Framework"
  language: "Python"
  author: "LangChain Team"
```

### Text Chunking (`src/config.py`)

```python
TextSplitterSettings(
    chunk_size=4000,
    chunk_overlap=200,
    separators=["\n---\n", "\n\n", "\n## ", ...]
)
```

---

## 🔒 Security

For security measures (prompt injection, XSS, rate limiting, CORS, API key handling, and deployment checklist), see **[SECURITY.md](SECURITY.md)**. **Do not commit `.env` or real API keys**; use `.env.example` as a template and keep secrets local or in your host’s env config.

---

## 💡 Usage

### Search for Tools

```python
import requests

response = requests.post("http://localhost:8080/search/unique-titles", json={
    "query_text": "python agent framework with memory",
    "category": "Framework",
    "language": "Python",
    "min_stars": 1000,
    "limit": 5
})

results = response.json()["results"]
for tool in results:
    print(f"{tool['title']} - {tool['stars']} stars")
```

### Ask Questions with RAG

```python
response = requests.post("http://localhost:8080/search/ask", json={
    "query_text": "What are the best Python frameworks for building AI agents?",
    "category": "Framework",
    "language": "Python",
    "limit": 5,
    "provider": "openrouter"
})

answer = response.json()["answer"]
sources = response.json()["sources"]
```

---

## 📡 API Reference

### POST `/search/unique-titles`

Search for unique tools/articles.

**Request:**
```json
{
  "query_text": "string",
  "category": "Framework | Library | Platform | Tool",
  "language": "Python | JavaScript | TypeScript | Go | Rust",
  "source_type": "github_repo | rss_article | documentation",
  "min_stars": 100,
  "limit": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "title": "LangChain",
      "source_name": "GitHub",
      "source_author": "langchain-ai",
      "url": "https://github.com/langchain-ai/langchain",
      "category": "Framework",
      "language": "Python",
      "stars": 50000,
      "features": ["agents", "chains", "memory"],
      "source_type": "github_repo",
      "score": 0.95
    }
  ]
}
```

### POST `/search/ask`

RAG-powered question answering (non-streaming).

**Request:**
```json
{
  "query_text": "How do I build a conversational AI agent?",
  "category": "Framework",
  "limit": 5,
  "provider": "openrouter",
  "model": "anthropic/claude-3-sonnet"
}
```

**Response:**
```json
{
  "query": "How do I build a conversational AI agent?",
  "answer": "To build a conversational AI agent...",
  "sources": [...],
  "provider": "openrouter",
  "model": "anthropic/claude-3-sonnet",
  "finish_reason": "stop"
}
```

### POST `/search/ask/stream`

RAG-powered question answering (streaming).

Returns `text/plain` stream with chunks of generated text.

---

## 🛠️ Development

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy src/
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

---

## 🚢 Deployment

### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --config cloudbuild_fastapi.yaml

# Or use the deploy script
chmod +x deploy_fastapi.sh
./deploy_fastapi.sh
```

### Prefect Cloud Scheduling

```bash
# Deploy flows to Prefect Cloud
prefect deploy --all --prefect-file prefect-cloud.yaml

# Schedule daily ingestion
prefect deployment run 'ai_tools_ingest_flow/production' --param enable_rss=true
```

### Ready for GitHub & Vercel

**Before you push to GitHub:**  
- Ensure `.env` and `frontend/.env` (and `frontend/.env.production`, `frontend/.env.development`) are **not** staged; they are in `.gitignore` and should never be committed. Run `git status` and confirm no `.env` files are listed.

**After pushing to GitHub, to deploy the frontend on Vercel:**  
1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project** → Import your `agents-tool-rag` repo.  
2. Set **Root Directory** to `frontend` (the React app lives there).  
3. Add **Environment Variables** in Vercel: `VITE_BACKEND_URL` = your FastAPI URL (e.g. Cloud Run), `VITE_API_KEY` = your backend API key.  
4. Deploy. Then add **https://agents-tool-rag.vercel.app** to the backend **ALLOWED_ORIGINS** and redeploy the backend so CORS allows the frontend.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- **LangChain** for the amazing agent framework
- **Qdrant** for the vector database
- **Supabase** for PostgreSQL hosting
- **FastAPI** for the API framework
- **Gradio** for the UI
- **Prefect** for workflow orchestration

---

## 📧 Contact

For questions or feedback, open an issue on GitHub.

**Built with ❤️ for the AI agent community**
