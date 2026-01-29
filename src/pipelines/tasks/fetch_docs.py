from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from prefect import task
from prefect.cache_policies import NO_CACHE
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.infrastructure.supabase.init_session import init_session
from src.models.article_models import DocSite, ToolItem
from src.models.sql_models import AIAgentTool
from src.utils.logger_util import setup_logging


@task(
    task_run_name="fetch_documentation-{doc_site.name}",
    description="Fetch documentation from a documentation site.",
    retries=2,
    retry_delay_seconds=120,
    cache_policy=NO_CACHE,
)
def fetch_documentation(
    doc_site: DocSite,
    engine: Engine,
    max_pages: int = 20,
) -> list[ToolItem]:
    """Fetch documentation from a documentation site.

    Scrapes documentation pages and converts them to ToolItem objects.
    Uses sitemap if available, otherwise crawls from the main page.

    Args:
        doc_site (DocSite): Documentation site configuration.
        engine (Engine): SQLAlchemy engine for database connection.
        max_pages (int): Maximum number of pages to scrape. Defaults to 20.

    Returns:
        list[ToolItem]: List of ToolItem objects for documentation pages.

    Raises:
        RuntimeError: If the documentation fetch fails.
        Exception: For unexpected errors during execution.
    """

    logger = setup_logging()
    session: Session = init_session(engine)
    items: list[ToolItem] = []
    visited_urls: set[str] = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AI-Agent-Tools-Bot/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        # Try to fetch sitemap first
        sitemap_urls = _fetch_sitemap(doc_site.url, doc_site.base_url, headers, logger)

        if sitemap_urls:
            logger.info(f"Found {len(sitemap_urls)} URLs in sitemap for {doc_site.name}")
            urls_to_scrape = list(sitemap_urls)[:max_pages]
        else:
            logger.info(f"No sitemap found for {doc_site.name}, will scrape main page")
            urls_to_scrape = [doc_site.url]

        for url in urls_to_scrape:
            if url in visited_urls:
                continue

            # Check if already in database
            if session.query(AIAgentTool).filter_by(url=url).first():
                logger.info(f"Skipping already stored doc: {url}")
                visited_urls.add(url)
                continue

            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                continue

            visited_urls.add(url)

            try:
                soup = BeautifulSoup(response.content, "html.parser")

                # Extract title
                title = _extract_title(soup, doc_site.name)

                # Extract main content
                content_html = _extract_main_content(soup)
                if not content_html:
                    logger.warning(f"No content found for {url}")
                    continue

                # Convert to markdown
                content_md = md(
                    str(content_html),
                    strip=["script", "style", "nav", "header", "footer"],
                    heading_style="ATX",
                    bullets="*",
                    autolinks=True,
                )

                # Clean up markdown
                content_md = "\n".join(
                    line.strip() for line in content_md.splitlines() if line.strip()
                )

                if not content_md or len(content_md) < 100:
                    logger.warning(f"Content too short for {url}, skipping")
                    continue

                # Extract features from headings
                features = _extract_features(soup)

                # Create ToolItem
                tool_item = ToolItem(
                    source_name=doc_site.name,
                    source_author=getattr(doc_site, "author", doc_site.name),
                    title=title,
                    url=url,
                    content=content_md[:15000],  # Limit to 15k chars
                    authors=[getattr(doc_site, "author", doc_site.name)],
                    published_at=datetime.now().isoformat(),
                    category=getattr(doc_site, "category", None),
                    language=getattr(doc_site, "language", None),
                    stars=None,  # Not available for docs
                    features=features[:10] if features else None,  # Limit to 10
                    license_type=None,  # Not available for docs
                    source_type="documentation",
                )
                items.append(tool_item)
                logger.info(f"Scraped doc page: {title} from {url}")

            except Exception as e:
                logger.error(f"Error processing doc page {url}: {e}")
                continue

        logger.info(f"Fetched {len(items)} documentation pages from {doc_site.name}")
        return items

    except Exception as e:
        logger.error(f"Unexpected error in fetch_documentation for {doc_site.name}: {e}")
        raise
    finally:
        session.close()
        logger.info(f"Database session closed for {doc_site.name}")


def _fetch_sitemap(start_url: str, base_url: str, headers: dict, logger) -> set[str]:
    """Try to fetch sitemap.xml and extract URLs.

    Args:
        start_url (str): Starting URL of the documentation.
        base_url (str): Base URL for the site.
        headers (dict): HTTP headers for requests.
        logger: Logger instance.

    Returns:
        set[str]: Set of URLs from sitemap, or empty set if not found.
    """
    sitemap_urls = []

    # Try common sitemap locations
    sitemap_locations = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
        urljoin(start_url, "sitemap.xml"),
    ]

    for sitemap_url in sitemap_locations:
        try:
            response = requests.get(sitemap_url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "xml")
                # Extract URLs from sitemap
                for loc in soup.find_all("loc"):
                    url = loc.get_text(strip=True)
                    # Filter for documentation pages only
                    if url and ("/docs/" in url or "/documentation/" in url or base_url in url):
                        sitemap_urls.append(url)
                if sitemap_urls:
                    logger.info(f"Found sitemap at {sitemap_url}")
                    return set(sitemap_urls)
        except Exception as e:
            logger.debug(f"No sitemap at {sitemap_url}: {e}")
            continue

    return set()


def _extract_title(soup: BeautifulSoup, default: str) -> str:
    """Extract page title from HTML.

    Args:
        soup (BeautifulSoup): Parsed HTML.
        default (str): Default title if not found.

    Returns:
        str: Page title.
    """
    # Try multiple selectors
    title = (
        soup.find("h1")
        or soup.find("title")
        or soup.find("meta", {"property": "og:title"})
        or soup.find("meta", {"name": "title"})
    )

    if title:
        if title.name == "meta":
            return title.get("content", default)
        return title.get_text(strip=True)

    return default


def _extract_main_content(soup: BeautifulSoup) -> BeautifulSoup | None:
    """Extract main content from HTML.

    Tries various selectors to find the main documentation content.

    Args:
        soup (BeautifulSoup): Parsed HTML.

    Returns:
        BeautifulSoup | None: Main content element or None.
    """
    # Try common documentation content selectors
    content_selectors = [
        {"name": "main"},
        {"name": "article"},
        {"class_": "content"},
        {"class_": "documentation"},
        {"class_": "markdown"},
        {"id": "content"},
        {"id": "main-content"},
        {"role": "main"},
    ]

    for selector in content_selectors:
        content = soup.find(**selector)
        if content and len(content.get_text(strip=True)) > 100:
            return content

    # Fallback: return body
    return soup.find("body")


def _extract_features(soup: BeautifulSoup) -> list[str]:
    """Extract features from page headings.

    Args:
        soup (BeautifulSoup): Parsed HTML.

    Returns:
        list[str]: List of feature names from headings.
    """
    features = []
    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True)
        if text and len(text) < 100:  # Reasonable heading length
            features.append(text)
    return features


def load_doc_sites(yaml_path: str) -> list[DocSite]:
    """Load documentation sites from YAML file.

    Args:
        yaml_path (str): Path to YAML file.

    Returns:
        list[DocSite]: List of DocSite objects.
    """
    try:
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        sites = data.get("sites", [])
        return [DocSite(**site) for site in sites]
    except Exception as e:
        logger = setup_logging()
        logger.error(f"Failed to load doc sites from {yaml_path}: {e}")
        return []
