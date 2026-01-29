import base64
from datetime import datetime

import requests
from prefect import task
from prefect.cache_policies import NO_CACHE
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.config import settings
from src.infrastructure.supabase.init_session import init_session
from src.models.article_models import ToolItem
from src.models.sql_models import AIAgentTool
from src.utils.logger_util import setup_logging


@task(
    task_run_name="fetch_github_repos",
    description="Fetch AI agent repositories from GitHub API.",
    retries=2,
    retry_delay_seconds=120,
    cache_policy=NO_CACHE,
)
def fetch_github_repos(
    engine: Engine,
    search_query: str | None = None,
    max_repos: int | None = None,
    min_stars: int | None = None,
) -> list[ToolItem]:
    """Fetch AI agent tool repositories from GitHub API.

    Uses GitHub Search API to find repositories matching the search query.
    Fetches README content and extracts metadata (stars, language, license).

    Args:
        engine (Engine): SQLAlchemy engine for database connection.
        search_query (str | None): GitHub search query. Defaults to config value.
        max_repos (int | None): Maximum repos to fetch. Defaults to config value.
        min_stars (int | None): Minimum GitHub stars. Defaults to config value.

    Returns:
        list[ToolItem]: List of ToolItem objects for GitHub repositories.

    Raises:
        RuntimeError: If the GitHub API fetch fails.
        Exception: For unexpected errors during execution.
    """

    logger = setup_logging()
    github_config = settings.github

    # Use config defaults if not provided
    search_query = search_query or github_config.search_query
    max_repos = max_repos or github_config.max_repos
    min_stars = min_stars or github_config.min_stars

    session: Session = init_session(engine)
    items: list[ToolItem] = []

    # Build GitHub API headers
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_config.api_key:
        headers["Authorization"] = f"token {github_config.api_key}"

    try:
        # Search for repositories
        search_url = "https://api.github.com/search/repositories"
        params = {
            "q": f"{search_query} stars:>={min_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": min(max_repos, 100),  # GitHub max is 100 per page
        }

        logger.info(f"Searching GitHub for: {params['q']}")

        try:
            response = requests.get(search_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to search GitHub repositories: {e}")
            raise RuntimeError(f"GitHub API search failed: {e}") from e

        data = response.json()
        repos = data.get("items", [])
        logger.info(f"Found {len(repos)} repositories matching criteria")

        for repo in repos[:max_repos]:
            try:
                # Check if already in database
                repo_url = repo.get("html_url", "")
                if not repo_url or session.query(AIAgentTool).filter_by(url=repo_url).first():
                    logger.info(f"Skipping already stored repo: {repo_url}")
                    continue

                # Extract basic metadata
                title = repo.get("name", "Untitled")
                full_name = repo.get("full_name", "")
                description = repo.get("description", "")
                stars = repo.get("stargazers_count", 0)
                language = repo.get("language", None)
                license_info = repo.get("license", {})
                license_type = license_info.get("spdx_id", None) if license_info else None
                topics = repo.get("topics", [])
                created_at = repo.get("created_at", datetime.now().isoformat())

                # Determine category from topics
                category = _determine_category(topics, description)

                # Fetch README content
                readme_content = _fetch_readme(full_name, headers, logger)

                if not readme_content:
                    logger.warning(f"Skipping repo '{full_name}' with no README content")
                    continue

                # Combine description and README for content
                content = f"# {title}\n\n{description}\n\n{readme_content}"

                # Extract features from topics
                features = topics[:10] if topics else None  # Limit to first 10 topics

                tool_item = ToolItem(
                    source_name="GitHub",
                    source_author=repo.get("owner", {}).get("login", "Unknown"),
                    title=title,
                    url=repo_url,
                    content=content,
                    authors=[repo.get("owner", {}).get("login", "Unknown")],
                    published_at=created_at,
                    category=category,
                    language=language,
                    stars=stars,
                    features=features,
                    license_type=license_type,
                    source_type="github_repo",
                )
                items.append(tool_item)
                logger.info(
                    f"Fetched repo: {full_name} ({stars} stars, {language or 'Unknown'})"
                )

            except Exception as e:
                logger.error(f"Error processing repo {repo.get('full_name', 'Unknown')}: {e}")
                continue

        logger.info(f"Fetched {len(items)} new GitHub repositories")
        return items

    except Exception as e:
        logger.error(f"Unexpected error in fetch_github_repos: {e}")
        raise
    finally:
        session.close()
        logger.info("Database session closed for GitHub fetch")


def _fetch_readme(full_name: str, headers: dict, logger) -> str:
    """Fetch README content from GitHub repository.

    Args:
        full_name (str): Full repository name (owner/repo).
        headers (dict): GitHub API headers with authentication.
        logger: Logger instance.

    Returns:
        str: README content in markdown format, or empty string if not found.
    """
    try:
        readme_url = f"https://api.github.com/repos/{full_name}/readme"
        response = requests.get(readme_url, headers=headers, timeout=15)
        response.raise_for_status()

        readme_data = response.json()
        # README content is base64 encoded
        content_encoded = readme_data.get("content", "")
        if content_encoded:
            content_decoded = base64.b64decode(content_encoded).decode("utf-8")
            # Limit README length to avoid huge documents
            return content_decoded[:10000]  # First 10k chars
        return ""
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch README for {full_name}: {e}")
        return ""
    except Exception as e:
        logger.warning(f"Error decoding README for {full_name}: {e}")
        return ""


def _determine_category(topics: list[str], description: str) -> str | None:
    """Determine tool category from GitHub topics and description.

    Args:
        topics (list[str]): GitHub repository topics.
        description (str): Repository description.

    Returns:
        str | None: Category (Framework, Library, Platform, Tool) or None.
    """
    topics_lower = [t.lower() for t in topics]
    desc_lower = description.lower()

    # Framework indicators
    if any(
        word in topics_lower or word in desc_lower
        for word in ["framework", "langchain", "autogpt", "crewai"]
    ):
        return "Framework"

    # Library indicators
    if any(word in topics_lower or word in desc_lower for word in ["library", "sdk", "api"]):
        return "Library"

    # Platform indicators
    if any(
        word in topics_lower or word in desc_lower for word in ["platform", "service", "cloud"]
    ):
        return "Platform"

    # Default to Tool
    if any(word in topics_lower or word in desc_lower for word in ["tool", "agent", "ai"]):
        return "Tool"

    return None
