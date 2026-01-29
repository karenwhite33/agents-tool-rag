# Data Sources Documentation

This document provides detailed information about all data sources used in the AI Agent Tools Search Engine.

---

## 📰 RSS Feeds

### Overview

RSS feeds provide the latest articles, tutorials, and news about AI agents and frameworks from various blogs and publications.

### Configuration

**File**: `src/configs/feeds_rss.yaml`

```yaml
feeds:
- name: "Feed Name"
  author: "Feed Author"
  url: "https://example.com/feed"
```

### Current Feeds

| Feed Name | Author | URL | Content Type |
|-----------|--------|-----|--------------|
| LangChain Blog | LangChain Team | https://blog.langchain.dev/feed/ | Framework updates, tutorials |
| Hugging Face Blog | Hugging Face Team | https://huggingface.co/blog/feed.xml | Model releases, research |
| Towards Data Science | Medium Community | https://towardsdatascience.com/feed | AI/ML articles |
| TechCrunch AI | TechCrunch | https://techcrunch.com/tag/artificial-intelligence/feed/ | AI industry news |
| The Batch (DeepLearning.AI) | Andrew Ng | https://www.deeplearning.ai/the-batch/feed/ | Weekly AI newsletter |
| Dev.to AI Articles | Dev.to Community | https://dev.to/feed/tag/ai | Developer tutorials |

### Data Extraction

**Fields Extracted:**
- `title`: Article title
- `url`: Article URL
- `content`: Full article content (HTML → Markdown)
- `published_at`: Publication date
- `source_name`: Feed name
- `source_author`: Feed author
- `authors`: Article authors (from `<dc:creator>`)

**Processing:**
1. Fetch RSS XML
2. Parse with BeautifulSoup (xml parser)
3. Skip paywalled content (detects "Read more" self-links)
4. Convert HTML to Markdown with markdownify
5. Extract category from `<category>` tags
6. Detect language from content (first 500 chars)

### Rate Limits

- No authentication required
- Recommended: Poll every 6-24 hours
- Respect `<ttl>` if present in feed

### Adding New Feeds

1. Find RSS/Atom feed URL (usually `/feed` or `/rss`)
2. Add to `src/configs/feeds_rss.yaml`
3. Test with: `python -m src.pipelines.tasks.fetch_tools`
4. Run ingestion flow

---

## 📦 GitHub Repositories

### Overview

GitHub API provides metadata about AI agent frameworks, libraries, and tools, including stars, language, license, and README content.

### Authentication

**Required**: GitHub Personal Access Token

```bash
GITHUB__API_KEY=ghp_your_token_here
```

**Permissions**: `public_repo`, `read:org`

**Rate Limits:**
- Without token: 60 requests/hour
- With token: 5000 requests/hour

### Configuration

**Settings** (`src/config.py`):

```python
GitHubSettings(
    api_key="",                      # Required
    search_query="AI agent framework",
    min_stars=100,
    max_repos=50,
    topics=["ai", "agent", "llm", "langchain", "autogpt"]
)
```

### API Endpoints Used

#### 1. Search Repositories

```
GET https://api.github.com/search/repositories
?q=AI+agent+framework+stars:>=100
&sort=stars
&order=desc
&per_page=100
```

**Returns**: List of repositories matching criteria

#### 2. Get Repository Details

```
GET https://api.github.com/repos/{owner}/{repo}
```

**Returns**: Full repo metadata (stars, language, license, topics)

#### 3. Get README

```
GET https://api.github.com/repos/{owner}/{repo}/readme
```

**Returns**: Base64-encoded README content

### Data Extraction

**Fields Extracted:**
- `title`: Repository name
- `url`: Repository HTML URL
- `content`: Description + README (first 10k chars)
- `source_name`: "GitHub"
- `source_author`: Repository owner
- `authors`: [Repository owner]
- `category`: Determined from topics/description
- `language`: Primary programming language
- `stars`: Stargazers count
- `features`: Repository topics (first 10)
- `license_type`: SPDX license identifier
- `source_type`: "github_repo"
- `published_at`: Repository creation date

### Category Detection

| Keywords in Topics/Description | Category |
|-------------------------------|----------|
| framework, langchain, autogpt, crewai | Framework |
| library, sdk, api | Library |
| platform, service, cloud | Platform |
| tool, agent, ai | Tool |

### Adding Custom Searches

Edit `search_query` in config:

```python
# Search for Python-only repos
GITHUB__SEARCH_QUERY="AI agent language:python"

# Search for repos updated recently
GITHUB__SEARCH_QUERY="AI agent pushed:>2024-01-01"

# Combine filters
GITHUB__SEARCH_QUERY="LLM agent language:python stars:>1000"
```

See [GitHub Search Syntax](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories)

### Troubleshooting

**Problem**: 403 Rate Limit Exceeded

**Solution**:
1. Add `GITHUB__API_KEY` to `.env`
2. Reduce `max_repos`
3. Check rate limit: `curl -H "Authorization: token $GITHUB__API_KEY" https://api.github.com/rate_limit`

---

## 📚 Documentation Sites

### Overview

Web scraping of official documentation sites for AI agent frameworks provides comprehensive, structured content.

### Configuration

**File**: `src/configs/doc_sites.yaml`

```yaml
sites:
- name: "Framework Name"
  url: "https://docs.framework.com/"
  base_url: "https://docs.framework.com"
  category: "Framework"
  language: "Python"
  author: "Framework Team"
```

### Current Sites

| Name | URL | Category | Language |
|------|-----|----------|----------|
| LangChain | https://python.langchain.com/docs/ | Framework | Python |
| CrewAI | https://docs.crewai.com/ | Framework | Python |
| LlamaIndex | https://docs.llamaindex.ai/ | Framework | Python |
| Hugging Face Transformers | https://huggingface.co/docs/transformers/ | Library | Python |
| Semantic Kernel | https://learn.microsoft.com/en-us/semantic-kernel/ | Framework | Python |
| AutoGPT | https://docs.agpt.co/ | Platform | Python |

### Scraping Strategy

#### 1. Sitemap Discovery

Try these URLs in order:
- `{base_url}/sitemap.xml`
- `{base_url}/sitemap_index.xml`
- `{url}/sitemap.xml`

If found, extract all URLs containing `/docs/` or `/documentation/`.

#### 2. Fallback: Main Page

If no sitemap, scrape the main docs page.

#### 3. Content Extraction

**Selectors Tried (in order):**
```html
<main>
<article>
<div class="content">
<div class="documentation">
<div class="markdown">
<div id="content">
<div id="main-content">
<div role="main">
```

Falls back to `<body>` if none found.

#### 4. Processing

1. Convert HTML to Markdown
2. Strip scripts, styles, nav, header, footer
3. Extract title from `<h1>` or `<title>`
4. Extract features from `<h2>` and `<h3>` headings
5. Limit content to first 15k characters

### Data Extraction

**Fields Extracted:**
- `title`: Page title
- `url`: Page URL
- `content`: Page content (markdownified, max 15k chars)
- `source_name`: Documentation site name
- `source_author`: Site author/team
- `authors`: [Site author]
- `category`: From config
- `language`: From config
- `features`: Extracted from headings (first 10)
- `source_type`: "documentation"
- `published_at`: Current datetime (docs don't have pub dates)

### Scraping Best Practices

1. **Respect robots.txt**: Check site's robots.txt first
2. **Rate Limiting**: Max 1 request per second per domain
3. **User-Agent**: Identifies as `AI-Agent-Tools-Bot/1.0`
4. **Error Handling**: Skip pages that fail (403, 404, etc.)
5. **Limits**: Max 20 pages per site (configurable)

### Adding New Documentation Sites

1. Check if site has sitemap: `https://docs.example.com/sitemap.xml`
2. Inspect HTML structure: Find main content selector
3. Add to `src/configs/doc_sites.yaml`
4. Test with: `python -m src.pipelines.tasks.fetch_docs`
5. Adjust selectors in `_extract_main_content()` if needed

### Troubleshooting

**Problem**: 403 Forbidden or Connection Refused

**Causes:**
- Site blocks scrapers
- Rate limiting
- Cloudflare protection

**Solutions:**
1. Use official API if available
2. Reduce frequency (scrape less often)
3. Check if site has RSS feed for updates
4. Contact site owner for permission/API access

**Problem**: Empty content extracted

**Causes:**
- JavaScript-rendered content
- Non-standard HTML structure

**Solutions:**
1. Inspect page HTML (View Source)
2. Look for content container selector
3. Update `_extract_main_content()` selectors
4. Consider using Selenium for JS-heavy sites

---

## 🔄 Data Pipeline

### Flow Diagram

```
RSS Feeds ────┐
              │
GitHub API ───┼──> fetch_*() ──> ToolItem[]
              │
Docs Sites ───┘
                       │
                       ▼
              ingest_tools()
                       │
                       ▼
         PostgreSQL (ai_agent_tools)
                       │
                       ▼
              RecursiveTextSplitter
                       │
                       ▼
         Generate Embeddings (Dense + Sparse)
                       │
                       ▼
         Qdrant Vector Store (with payload)
```

### Scheduling with Prefect

```python
# Deploy to Prefect Cloud
prefect deploy --all

# Schedule daily ingestion at 2 AM
prefect deployment schedule create \
  ai_tools_ingest_flow/production \
  --cron "0 2 * * *" \
  --timezone "America/New_York"
```

### Monitoring

- **Logs**: Check Prefect UI for flow runs
- **Database**: `SELECT COUNT(*), source_type FROM ai_agent_tools GROUP BY source_type;`
- **Qdrant**: Check collection stats in dashboard

---

## 📊 Data Statistics

### Typical Ingestion Volumes

| Source | Items per Run | Update Frequency | Storage Size |
|--------|---------------|------------------|--------------|
| RSS Feeds | 50-200 articles | Daily | ~5-20 MB |
| GitHub | 50-100 repos | Weekly | ~10-30 MB |
| Docs | 20-50 pages/site | Monthly | ~5-15 MB |

### Vector Store Size

- **Chunks**: ~5-10 per item
- **Vectors**: 768-dim dense + sparse
- **Payload**: ~2-5 KB per chunk
- **Total**: ~500 MB for 10k items

---

## 🔒 Data Privacy & Compliance

### Public Data Only

All sources are public:
- RSS feeds are publicly accessible
- GitHub repos are public repositories
- Documentation sites are publicly available

### Attribution

- Original URLs preserved
- Authors/sources clearly labeled
- No modification of content (except formatting)

### Removal Requests

To remove your content:
1. Open a GitHub issue
2. Provide URL(s) to remove
3. We'll remove within 48 hours

---

## 📝 Contributing New Sources

Want to add a new data source? Follow these steps:

1. **Fork the repository**
2. **Create new fetch task**: `src/pipelines/tasks/fetch_newsource.py`
3. **Implement**: Return `list[ToolItem]`
4. **Add config**: Update `src/config.py` or create YAML
5. **Update flow**: Add to `tools_ingestion_flow.py`
6. **Test**: Run locally
7. **Document**: Update this file
8. **Pull request**: Submit for review

### Template

```python
@task
def fetch_new_source(engine: Engine) -> list[ToolItem]:
    """Fetch from new source."""
    items = []
    # Your implementation here
    return items
```

---

For questions, open an issue on GitHub!
