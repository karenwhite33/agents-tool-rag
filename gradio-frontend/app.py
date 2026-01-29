import os

import gradio as gr
import markdown
import requests
import yaml
from dotenv import load_dotenv

try:
    from src.api.models.provider_models import MODEL_REGISTRY
except ImportError as e:
    raise ImportError(
        "Could not import MODEL_REGISTRY from src.api.models.provider_models. "
        "Check the path and file existence."
    ) from e

# Initialize environment variables
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
API_BASE_URL = f"{BACKEND_URL}/search"


# Load feeds from YAML
def load_feeds():
    """Load feeds from the YAML configuration file.
    Returns:
        list: List of feeds with their details.
    """
    feeds_path = os.path.join(os.path.dirname(__file__), "../src/configs/feeds_rss.yaml")
    with open(feeds_path) as f:
        feeds_yaml = yaml.safe_load(f)
    return feeds_yaml.get("feeds", [])


feeds = load_feeds()
feed_names = [f["name"] for f in feeds]
feed_authors = [f["author"] for f in feeds]


# -----------------------
# API helpers
# -----------------------
def fetch_unique_titles(payload):
    """
    Fetch unique article titles based on the search criteria.

    Args:
        payload (dict): The search criteria including query_text, feed_author,
                        feed_name, limit, and optional title_keywords.
    Returns:
        list: A list of articles matching the criteria.
    Raises:
        Exception: If the API request fails.
    """
    try:
        resp = requests.post(f"{API_BASE_URL}/unique-titles", json=payload)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        raise Exception(f"Failed to fetch titles: {str(e)}") from e


def call_ai(payload, streaming=True):
    """ "
    Call the AI endpoint with the given payload.
    Args:
        payload (dict): The payload to send to the AI endpoint.
        streaming (bool): Whether to use streaming or non-streaming endpoint.
    Yields:
        tuple: A tuple containing the type of response and the response text.
    """
    endpoint = f"{API_BASE_URL}/ask/stream" if streaming else f"{API_BASE_URL}/ask"
    answer_text = ""
    try:
        if streaming:
            with requests.post(endpoint, json=payload, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                    if not chunk:
                        continue
                    if chunk.startswith("__model_used__:"):
                        yield "model", chunk.replace("__model_used__:", "").strip()
                    elif chunk.startswith("__error__"):
                        yield "error", "Request failed. Please try again later."
                        break
                    elif chunk.startswith("__truncated__"):
                        yield "truncated", "AI response truncated due to token limit."
                    else:
                        answer_text += chunk
                        yield "text", answer_text
        else:
            resp = requests.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            answer_text = data.get("answer", "")
            yield "text", answer_text
            if data.get("finish_reason") == "length":
                yield "truncated", "AI response truncated due to token limit."
    except Exception as e:
        yield "error", f"Request failed: {str(e)}"


def get_models_for_provider(provider):
    """
    Get available models for a provider

    Args:
        provider (str): The name of the provider (e.g., "openrouter", "openai")
    Returns:
        list: List of model names available for the provider
    """
    provider_key = provider.lower()
    try:
        config = MODEL_REGISTRY.get_config(provider_key)
        return (
            ["Automatic Model Selection (Model Routing)"]
            + ([config.primary_model] if config.primary_model else [])
            + list(config.candidate_models)
        )
    except Exception:
        return ["Automatic Model Selection (Model Routing)"]


# -----------------------
# Gradio interface functions
# -----------------------
def handle_search_articles(
    query_text,
    feed_name,
    feed_author,
    title_keywords,
    category,
    language,
    source_type,
    min_stars,
    limit,
):
    """
    Handle AI agent tool search

    Args:
        query_text (str): The text to search for.
        feed_name (str): The name of the feed (legacy).
        feed_author (str): The author of the feed (legacy).
        title_keywords (str): Keywords to search for in titles.
        category (str): Filter by category.
        language (str): Filter by programming language.
        source_type (str): Filter by source type.
        min_stars (int): Filter by minimum GitHub stars.
        limit (int): The maximum number of results to return.
    Returns:
        str: HTML formatted string of search results or error message.
    Raises:
        Exception: If the API request fails.
    """
    if not query_text.strip():
        return "Please enter a query text."

    payload = {
        "query_text": query_text.strip().lower(),
        "feed_author": feed_author.strip() if feed_author else "",
        "feed_name": feed_name.strip() if feed_name else "",
        "title_keywords": title_keywords.strip().lower() if title_keywords else None,
        "category": category if category else None,
        "language": language if language else None,
        "source_type": source_type if source_type else None,
        "min_stars": int(min_stars) if min_stars > 0 else None,
        "limit": limit,
    }

    try:
        results = fetch_unique_titles(payload)
        if not results:
            return (
                "<div style='background: white; border: 1px solid #e5e7eb; border-radius: 8px; "
                "padding: 48px 24px; text-align: center;'>"
                "<i class='fas fa-search' style='font-size: 40px; color: #d1d5db; margin-bottom: 16px;'></i>"
                "<h3 style='color: #6b7280; font-size: 18px; margin: 0; font-weight: 500;'>No results found</h3>"
                "<p style='color: #9ca3af; font-size: 14px; margin: 8px 0 0 0;'>Try adjusting your search criteria</p>"
                "</div>"
            )

        html_output = """
        <style>
            .article-card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 24px;
                margin-bottom: 16px;
                transition: all 0.2s ease;
            }
            .article-card:hover {
                border-color: #d1d5db;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            .article-title {
                font-size: 20px;
                font-weight: 600;
                color: #111827;
                margin: 0 0 12px 0;
                line-height: 1.4;
            }
            .article-badges {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-bottom: 16px;
            }
            .badge {
                display: inline-flex;
                align-items: center;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                white-space: nowrap;
                border: 1px solid;
            }
            .badge-category {
                background: #f0fdf4;
                color: #166534;
                border-color: #bbf7d0;
            }
            .badge-language {
                background: #eff6ff;
                color: #1e40af;
                border-color: #bfdbfe;
            }
            .badge-stars {
                background: #fffbeb;
                color: #92400e;
                border-color: #fde68a;
            }
            .badge-source {
                background: #faf5ff;
                color: #6b21a8;
                border-color: #e9d5ff;
            }
            .article-meta {
                display: flex;
                flex-direction: column;
                gap: 6px;
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid #f3f4f6;
            }
            .meta-item {
                display: flex;
                align-items: center;
                font-size: 13px;
                color: #6b7280;
            }
            .meta-label {
                font-weight: 500;
                color: #9ca3af;
                margin-right: 8px;
                min-width: 60px;
            }
            .meta-value {
                color: #374151;
            }
            .article-link {
                color: #2563eb;
                text-decoration: none;
                font-weight: 400;
            }
            .article-link:hover {
                text-decoration: underline;
            }
            .features-list {
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid #f3f4f6;
            }
            .features-label {
                font-weight: 500;
                color: #9ca3af;
                font-size: 12px;
                margin-bottom: 4px;
            }
            .features-text {
                color: #6b7280;
                font-size: 13px;
                line-height: 1.6;
            }
        </style>
        """
        
        for item in results:
            # Build badges
            badges = []
            if item.get("category"):
                badges.append(
                    f"<span class='badge badge-category'>"
                    f"{item['category']}</span>"
                )
            if item.get("language"):
                badges.append(
                    f"<span class='badge badge-language'>"
                    f"{item['language']}</span>"
                )
            if item.get("stars") is not None:
                badges.append(
                    f"<span class='badge badge-stars'>"
                    f"<i class='fas fa-star' style='margin-right: 4px;'></i> {item['stars']:,}</span>"
                )
            if item.get("source_type"):
                source_icon = (
                    "<i class='fas fa-box'></i>"
                    if item["source_type"] == "github_repo"
                    else "<i class='fas fa-newspaper'></i>" if item["source_type"] == "rss_article" else "<i class='fas fa-book'></i>"
                )
                badges.append(
                    f"<span class='badge badge-source'>"
                    f"{source_icon} {item['source_type']}</span>"
                )

            badges_html = " ".join(badges)

            html_output += (
                f"<div class='article-card'>\n"
                f"    <h2 class='article-title'>{item.get('title', 'No title')}</h2>\n"
                f"    <div class='article-badges'>{badges_html}</div>\n"
                f"    <div class='article-meta'>\n"
                f"        <div class='meta-item'>"
                f"<span class='meta-label'><i class='fas fa-source' style='margin-right: 4px;'></i>Source:</span>"
                f"<span class='meta-value'>{item.get('source_name') or item.get('feed_name', 'N/A')}</span>"
                f"</div>\n"
                f"        <div class='meta-item'>"
                f"<span class='meta-label'><i class='fas fa-user' style='margin-right: 4px;'></i>Author:</span>"
                f"<span class='meta-value'>{item.get('source_author') or item.get('feed_author', 'N/A')}</span>"
                f"</div>\n"
                f"        <div class='meta-item'>"
                f"<span class='meta-label'><i class='fas fa-link' style='margin-right: 4px;'></i>URL:</span>"
                f"<a href='{item.get('url', '#')}' target='_blank' class='article-link'>"
                f"{item.get('url', 'No URL')}</a>"
                f"</div>\n"
            )

            if item.get("features"):
                features_html = ", ".join(item["features"][:5])  # Show first 5 features
                html_output += (
                    f"        <div class='features-list'>\n"
                    f"            <div class='features-label'><i class='fas fa-list' style='margin-right: 4px;'></i>Features:</div>\n"
                    f"            <div class='features-text'>{features_html}</div>\n"
                    f"        </div>\n"
                )

            html_output += "    </div>\n</div>\n"

        return html_output

    except Exception as e:
        return (
            f"<div style='background: #fef2f2; border: 1px solid #fecaca; "
            f"color: #991b1b; padding: 12px 16px; border-radius: 6px; "
            f"font-size: 14px;'>"
            f"<i class='fas fa-exclamation-circle' style='margin-right: 8px;'></i> Error: {str(e)}</div>"
        )


def handle_ai_question_streaming(
    query_text,
    feed_name,
    feed_author,
    category,
    language,
    source_type,
    min_stars,
    limit,
    provider,
    model,
):
    """
    Handle AI question with streaming

    Args:
        query_text (str): The question to ask the AI.
        feed_name (str): The name of the feed (legacy).
        feed_author (str): The author of the feed (legacy).
        category (str): Filter by category.
        language (str): Filter by programming language.
        source_type (str): Filter by source type.
        min_stars (int): Filter by minimum GitHub stars.
        limit (int): The maximum number of tools to consider.
        provider (str): The LLM provider to use.
        model (str): The specific model to use from the provider.
    Yields:
        tuple: (HTML formatted answer string, model info string)
    """
    if not query_text.strip():
        yield "Please enter a query text.", ""
        return

    if not provider or not model:
        yield "Please select provider and model.", ""
        return

    payload = {
        "query_text": query_text.strip().lower(),
        "feed_author": feed_author.strip() if feed_author else "",
        "feed_name": feed_name.strip() if feed_name else "",
        "category": category if category else None,
        "language": language if language else None,
        "source_type": source_type if source_type else None,
        "min_stars": int(min_stars) if min_stars > 0 else None,
        "limit": limit,
        "provider": provider.lower(),
    }

    if model != "Automatic Model Selection (Model Routing)":
        payload["model"] = model

    try:
        answer_html = ""
        model_info = "<i class='fas fa-search' style='margin-right: 6px;'></i>Searching for relevant information..."
        stored_model_info = None
        has_received_text = False
        yield answer_html, model_info

        for _, (event_type, content) in enumerate(call_ai(payload, streaming=True)):
            if event_type == "text":
                has_received_text = True
                # Update model_info if we have stored model info and this is the first text
                if stored_model_info and model_info.startswith("<i class='fas fa-search'"):
                    model_info = stored_model_info
                # Convert markdown to HTML
                html_content = markdown.markdown(content, extensions=["tables"])
                answer_html = (
                    f"<style>"
                    f".ai-answer {{"
                    f"    background: white;"
                    f"    border: 1px solid #e5e7eb;"
                    f"    border-radius: 8px;"
                    f"    padding: 24px;"
                    f"    font-size: 15px;"
                    f"    line-height: 1.7;"
                    f"    color: #374151;"
                    f"}}"
                    f".ai-answer h1, .ai-answer h2, .ai-answer h3 {{"
                    f"    color: #111827;"
                    f"    margin-top: 24px;"
                    f"    margin-bottom: 12px;"
                    f"    font-weight: 600;"
                    f"}}"
                    f".ai-answer p {{"
                    f"    color: #374151;"
                    f"    margin-bottom: 12px;"
                    f"}}"
                    f".ai-answer code {{"
                    f"    background: #f3f4f6;"
                    f"    color: #dc2626;"
                    f"    padding: 2px 6px;"
                    f"    border-radius: 4px;"
                    f"    font-size: 13px;"
                    f"}}"
                    f".ai-answer pre {{"
                    f"    background: #f9fafb;"
                    f"    border: 1px solid #e5e7eb;"
                    f"    color: #111827;"
                    f"    padding: 16px;"
                    f"    border-radius: 6px;"
                    f"    overflow-x: auto;"
                    f"}}"
                    f".ai-answer a {{"
                    f"    color: #2563eb;"
                    f"    text-decoration: none;"
                    f"}}"
                    f".ai-answer a:hover {{"
                    f"    text-decoration: underline;"
                    f"}}"
                    f".ai-answer ul, .ai-answer ol {{"
                    f"    color: #374151;"
                    f"    margin-left: 20px;"
                    f"}}"
                    f".ai-answer table {{"
                    f"    border-collapse: collapse;"
                    f"    width: 100%;"
                    f"    margin: 16px 0;"
                    f"}}"
                    f".ai-answer table th, .ai-answer table td {{"
                    f"    border: 1px solid #e5e7eb;"
                    f"    padding: 12px;"
                    f"    text-align: left;"
                    f"}}"
                    f".ai-answer table th {{"
                    f"    background: #f9fafb;"
                    f"    font-weight: 600;"
                    f"    color: #111827;"
                    f"}}"
                    f"</style>"
                    f"<div class='ai-answer'>\n"
                    f"    {html_content}\n"
                    f"</div>\n"
                )
                yield answer_html, model_info

            elif event_type == "model":
                stored_model_info = f"Provider: {provider} | Model: {content}"
                # Only update displayed model_info if we've already received text
                if has_received_text:
                    model_info = stored_model_info
                    yield answer_html, model_info

            elif event_type == "truncated":
                answer_html += (
                    f"<div style='background: #fffbeb; border: 1px solid #fde68a; "
                    f"color: #92400e; padding: 12px 16px; border-radius: 6px; "
                    f"margin-top: 16px; font-size: 14px;'>"
                    f"<i class='fas fa-exclamation-triangle' style='margin-right: 8px;'></i> {content}</div>"
                )
                yield answer_html, model_info

            elif event_type == "error":
                error_html = (
                    f"<div style='background: #fef2f2; border: 1px solid #fecaca; "
                    f"color: #991b1b; padding: 12px 16px; border-radius: 6px; "
                    f"font-size: 14px;'>"
                    f"<i class='fas fa-times-circle' style='margin-right: 8px;'></i> {content}</div>"
                )
                yield error_html, model_info
                break

    except Exception as e:
        error_html = (
            f"<div style='background: #fef2f2; border: 1px solid #fecaca; "
            f"color: #991b1b; padding: 12px 16px; border-radius: 6px; "
            f"font-size: 14px;'>"
            f"<i class='fas fa-exclamation-circle' style='margin-right: 8px;'></i> Error: {str(e)}</div>"
        )
        yield error_html, model_info


def handle_ai_question_non_streaming(
    query_text, feed_name, feed_author, category, language, source_type, min_stars, limit, provider, model
):
    """
    Handle AI question without streaming

    Args:
        query_text (str): The question to ask the AI.
        feed_name (str): The name of the feed (legacy).
        feed_author (str): The author of the feed (legacy).
        category (str): Filter by category.
        language (str): Filter by programming language.
        source_type (str): Filter by source type.
        min_stars (int): Filter by minimum GitHub stars.
        limit (int): The maximum number of tools to consider.
        provider (str): The LLM provider to use.
        model (str): The specific model to use from the provider.

    Returns:
        tuple: (HTML formatted answer string, model info string)
    """
    if not query_text.strip():
        return "Please enter a query text.", ""

    if not provider or not model:
        return "Please select provider and model.", ""

    payload = {
        "query_text": query_text.strip().lower(),
        "feed_author": feed_author.strip() if feed_author else "",
        "feed_name": feed_name.strip() if feed_name else "",
        "category": category if category else None,
        "language": language if language else None,
        "source_type": source_type if source_type else None,
        "min_stars": int(min_stars) if min_stars > 0 else None,
        "limit": limit,
        "provider": provider.lower(),
    }

    if model != "Automatic Model Selection (Model Routing)":
        payload["model"] = model

    try:
        answer_html = ""
        model_info = "<i class='fas fa-search' style='margin-right: 6px;'></i>Searching for relevant information..."
        stored_model_info = None
        has_received_text = False

        for event_type, content in call_ai(payload, streaming=False):
            if event_type == "text":
                has_received_text = True
                # Update model_info if we have stored model info and this is the first text
                if stored_model_info and model_info.startswith("<i class='fas fa-search'"):
                    model_info = stored_model_info
                html_content = markdown.markdown(content, extensions=["tables"])
                answer_html = (
                    f"<style>"
                    f".ai-answer {{"
                    f"    background: white;"
                    f"    border: 1px solid #e5e7eb;"
                    f"    border-radius: 8px;"
                    f"    padding: 24px;"
                    f"    font-size: 15px;"
                    f"    line-height: 1.7;"
                    f"    color: #374151;"
                    f"}}"
                    f".ai-answer h1, .ai-answer h2, .ai-answer h3 {{"
                    f"    color: #111827;"
                    f"    margin-top: 24px;"
                    f"    margin-bottom: 12px;"
                    f"    font-weight: 600;"
                    f"}}"
                    f".ai-answer p {{"
                    f"    color: #374151;"
                    f"    margin-bottom: 12px;"
                    f"}}"
                    f".ai-answer code {{"
                    f"    background: #f3f4f6;"
                    f"    color: #dc2626;"
                    f"    padding: 2px 6px;"
                    f"    border-radius: 4px;"
                    f"    font-size: 13px;"
                    f"}}"
                    f".ai-answer pre {{"
                    f"    background: #f9fafb;"
                    f"    border: 1px solid #e5e7eb;"
                    f"    color: #111827;"
                    f"    padding: 16px;"
                    f"    border-radius: 6px;"
                    f"    overflow-x: auto;"
                    f"}}"
                    f".ai-answer a {{"
                    f"    color: #2563eb;"
                    f"    text-decoration: none;"
                    f"}}"
                    f".ai-answer a:hover {{"
                    f"    text-decoration: underline;"
                    f"}}"
                    f".ai-answer ul, .ai-answer ol {{"
                    f"    color: #374151;"
                    f"    margin-left: 20px;"
                    f"}}"
                    f".ai-answer table {{"
                    f"    border-collapse: collapse;"
                    f"    width: 100%;"
                    f"    margin: 16px 0;"
                    f"}}"
                    f".ai-answer table th, .ai-answer table td {{"
                    f"    border: 1px solid #e5e7eb;"
                    f"    padding: 12px;"
                    f"    text-align: left;"
                    f"}}"
                    f".ai-answer table th {{"
                    f"    background: #f9fafb;"
                    f"    font-weight: 600;"
                    f"    color: #111827;"
                    f"}}"
                    f"</style>"
                    f"<div class='ai-answer'>\n"
                    f"{html_content}\n"
                    f"</div>\n"
                )
            elif event_type == "model":
                stored_model_info = f"Provider: {provider} | Model: {content}"
                # Only update displayed model_info if we've already received text
                if has_received_text:
                    model_info = stored_model_info
            elif event_type == "truncated":
                answer_html += (
                    f"<div style='background: #fffbeb; border: 1px solid #fde68a; "
                    f"color: #92400e; padding: 12px 16px; border-radius: 6px; "
                    f"margin-top: 16px; font-size: 14px;'>"
                    f"<i class='fas fa-exclamation-triangle' style='margin-right: 8px;'></i> {content}</div>"
                )
            elif event_type == "error":
                return (
                    f"<div style='background: #fef2f2; border: 1px solid #fecaca; "
                    f"color: #991b1b; padding: 12px 16px; border-radius: 6px; "
                    f"font-size: 14px;'>"
                    f"<i class='fas fa-times-circle' style='margin-right: 8px;'></i> {content}</div>",
                    model_info,
                )

        return answer_html, model_info

    except Exception as e:
        return (
            f"<div style='background: #fef2f2; border: 1px solid #fecaca; "
            f"color: #991b1b; padding: 12px 16px; border-radius: 6px; "
            f"font-size: 14px;'>"
            f"<i class='fas fa-exclamation-circle' style='margin-right: 8px;'></i> Error: {str(e)}</div>",
            f"Provider: {provider}",
        )


def update_model_choices(provider):
    """
    Update model choices based on selected provider
    Args:
        provider (str): The selected LLM provider
    Returns:
        gr.Dropdown: Updated model dropdown component
    """
    models = get_models_for_provider(provider)
    return gr.Dropdown(choices=models, value=models[0] if models else "", elem_classes=["white-dropdown"])


# -----------------------
# Gradio UI
# -----------------------
custom_theme = gr.themes.Default(
    primary_hue="slate",
    neutral_hue="slate",
).set(
    # Force white backgrounds everywhere
    block_background_fill="white",
    block_background_fill_dark="white",
    input_background_fill="white",
    input_background_fill_dark="white",
    panel_background_fill="white",
    panel_background_fill_dark="white",
)

# Aggressive CSS for Chrome
minimal_css = """
/* Hide Gradio footer */
footer { display: none !important; }

/* Primary button */
button[variant="primary"] {
    background: #2563eb !important;
    color: white !important;
    transition: all 0.15s ease !important;
}

/* Button pressed/active state - visual feedback */
button[variant="primary"]:active,
#submit-button:active,
button[variant="primary"].clicked,
#submit-button.clicked {
    transform: scale(0.97) !important;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2) !important;
    background: #1d4ed8 !important;
    background-color: #1d4ed8 !important;
}

/* Button hover state */
button[variant="primary"]:hover:not(:active),
#submit-button:hover:not(:active) {
    background: #1d4ed8 !important;
    background-color: #1d4ed8 !important;
}

/* FORCE LIGHT MODE - NO DARK MODE */
:root,
[data-theme],
[data-theme="dark"],
.dark {
    color-scheme: light !important;
}

/* Override dark mode on ALL input containers */
[data-theme="dark"] .gr-radio,
[data-theme="dark"] .gr-radio *,
[data-theme="dark"] .gr-dropdown,
[data-theme="dark"] .gr-dropdown *,
[data-theme="dark"] .gr-textbox,
[data-theme="dark"] .gr-textbox *,
[data-theme="dark"] .gr-slider,
[data-theme="dark"] .gr-slider *,
.dark .gr-radio,
.dark .gr-radio *,
.dark .gr-dropdown,
.dark .gr-dropdown *,
.dark .gr-textbox,
.dark .gr-textbox *,
.dark .gr-slider,
.dark .gr-slider * {
    background: white !important;
    background-color: white !important;
}

body,
.gradio-container,
[class*="gradio"] {
    color-scheme: light !important;
    background: white !important;
}

/* Force white BACKGROUNDS but keep text dark */
#sidebar-column {
    background-color: white !important;
    background: white !important;
}

/* Force white on sidebar container */
#sidebar-column {
    background-color: white !important;
    background: white !important;
}

/* Target ONLY inputs that need white - NOT radio labels */
#sidebar-column .gr-dropdown,
#sidebar-column .gr-dropdown *,
#sidebar-column .gr-textbox,
#sidebar-column .gr-textbox *,
#sidebar-column .gr-textbox input,
#sidebar-column .gr-textbox textarea,
#sidebar-column .gr-slider,
#sidebar-column .gr-slider input,
#sidebar-column .white-dropdown,
#sidebar-column .white-dropdown * {
    background-color: white !important;
    background: white !important;
    color: #111827 !important;
}

/* Target dropdowns specifically */
.white-dropdown,
.white-dropdown *,
body .white-dropdown,
body .white-dropdown *,
html body .white-dropdown,
html body .white-dropdown *,
[data-theme="dark"] .white-dropdown,
[data-theme="dark"] .white-dropdown *,
.dark .white-dropdown,
.dark .white-dropdown * {
    background-color: white !important;
    background: white !important;
    color: #111827 !important;
}

/* Keep ALL text dark and visible */
body,
body *,
label,
p,
span,
div,
h1, h2, h3, h4, h5, h6 {
    color: #111827 !important;
}

/* Header text must be visible */
.main-header,
.main-header *,
.main-header h1,
.main-header p {
    color: #111827 !important;
}

/* Sidebar text must be visible */
#sidebar-column label,
#sidebar-column p,
#sidebar-column span,
#sidebar-column div,
#sidebar-column h2,
#sidebar-column h3,
#sidebar-column h4 {
    color: #111827 !important;
}

/* Buttons must have color - OVERRIDE nuclear rule */
#sidebar-column button,
button[variant="primary"],
.gr-button.primary {
    background: #2563eb !important;
    background-color: #2563eb !important;
    color: white !important;
}

/* Radio buttons - Force white and use BORDER for selection */
.custom-radio-white label,
.gr-radio label,
.gr-radio-group label,
[data-theme="dark"] .custom-radio-white label,
[data-theme="dark"] .gr-radio label,
[data-theme="dark"] .gr-radio-group label,
.dark .custom-radio-white label,
.dark .gr-radio label,
.dark .gr-radio-group label {
    background: white !important;
    background-color: white !important;
    background-image: none !important;
    color: #111827 !important;
    border: 3px solid transparent !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

/* Radio button hover state */
.custom-radio-white label:hover,
.gr-radio label:hover,
.gr-radio-group label:hover {
    border-color: #93c5fd !important;
    background: #eff6ff !important;
}

/* Radio button SELECTED state - BLUE BORDER to show selection */
.custom-radio-white input[type="radio"]:checked + label,
.gr-radio input[type="radio"]:checked + label,
.gr-radio-group input[type="radio"]:checked + label,
[data-theme="dark"] .custom-radio-white input[type="radio"]:checked + label,
[data-theme="dark"] .gr-radio input[type="radio"]:checked + label,
[data-theme="dark"] .gr-radio-group input[type="radio"]:checked + label,
.dark .custom-radio-white input[type="radio"]:checked + label,
.dark .gr-radio input[type="radio"]:checked + label,
.dark .gr-radio-group input[type="radio"]:checked + label {
    background: #eff6ff !important;
    background-color: #eff6ff !important;
    background-image: none !important;
    border: 3px solid #2563eb !important;
    font-weight: 700 !important;
    color: #111827 !important;
}

/* Make sure radio inputs are clickable */
.gr-radio input[type="radio"],
.gr-radio-group input[type="radio"],
.custom-radio-white input[type="radio"] {
    cursor: pointer !important;
    opacity: 1 !important;
    z-index: 10 !important;
    pointer-events: auto !important;
    position: relative !important;
    width: auto !important;
    height: auto !important;
    margin: 0 !important;
    -webkit-appearance: radio !important;
    appearance: radio !important;
}

/* Ensure radio button labels are clickable */
.gr-radio label,
.gr-radio-group label,
.custom-radio-white label {
    pointer-events: auto !important;
    user-select: none !important;
    -webkit-user-select: none !important;
    cursor: pointer !important;
}

/* Radio button container */
.gr-radio,
.gr-radio-group {
    pointer-events: auto !important;
    position: relative !important;
}

/* Remove any overlay that might block clicks */
.gr-radio::before,
.gr-radio-group::before,
.gr-radio::after,
.gr-radio-group::after {
    display: none !important;
    pointer-events: none !important;
}


/* Buttons - keep original blue, but NO blue background on containers */
button[variant="primary"],
.gr-button.primary {
    background: #2563eb !important;
    background-color: #2563eb !important;
    color: white !important;
}

/* NO blue background on button containers or parents */
button[variant="primary"] *,
.gr-button.primary *,
button[variant="primary"]::before,
button[variant="primary"]::after {
    background: transparent !important;
    background-color: transparent !important;
}

/* Force light mode on all Gradio components */
.gr-block,
.gr-group,
.gr-form,
.gr-component {
    background: white !important;
    background-color: white !important;
}

/* Specifically target LLM Options group and all its children to prevent dark background */
.gr-group,
.gr-group *,
#sidebar-column .gr-group,
#sidebar-column .gr-group *,
#llm-options-group,
#llm-options-group *,
.gr-group .gr-dropdown,
.gr-group .gr-radio,
.gr-group .gr-textbox,
.gr-group label,
.gr-group div,
.gr-group span,
#llm-options-group .gr-dropdown,
#llm-options-group .gr-radio,
#llm-options-group .gr-textbox,
#llm-options-group label,
#llm-options-group div,
#llm-options-group span {
    background: white !important;
    background-color: white !important;
    background-image: none !important;
}
"""

with gr.Blocks(title="AI Agent Tools Search Engine", theme=custom_theme, css=minimal_css) as demo:
    # Header with Font Awesome CDN
    gr.HTML(
        r"""
        <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
        <style>
            .main-header {
                background: #f3f4f6 !important;
                padding: 40px 32px;
                border-bottom: 1px solid #e5e7eb;
                text-align: center;
                margin-bottom: 40px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            }
            .main-header h1 {
                color: #111827 !important;
                font-size: 32px;
                font-weight: 600;
                margin: 0;
                letter-spacing: -0.5px;
            }
            .main-header h1 * {
                color: #111827 !important;
            }
            .main-header p {
                color: #6b7280 !important;
                font-size: 15px;
                margin: 8px 0 0 0;
                font-weight: 400;
            }
            .main-header * {
                color: #111827 !important;
            }
            footer { display: none !important; }
            
        </style>
        <div class='main-header'>
            <h1>
                <i class='fas fa-robot' style='margin-right: 12px;'></i> AI Agent Tools Search Engine
            </h1>
            <p>
                Search AI frameworks, libraries, and documentation
            </p>
        </div>
        <script>
            // Force light mode
            document.documentElement.setAttribute('data-theme', 'light');
            document.body.setAttribute('data-theme', 'light');
            document.body.style.colorScheme = 'light';
            document.body.classList.remove('dark');
            
            // Watch for dark mode changes and revert
            const observer = new MutationObserver(() => {
                document.documentElement.setAttribute('data-theme', 'light');
                document.body.setAttribute('data-theme', 'light');
                document.body.classList.remove('dark');
            });
            observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] });
            observer.observe(document.body, { attributes: true, attributeFilter: ['data-theme', 'class'] });
            
            // Add visual click feedback to submit button
            document.addEventListener('DOMContentLoaded', function() {
                const submitButton = document.getElementById('submit-button');
                if (submitButton) {
                    submitButton.addEventListener('mousedown', function() {
                        this.classList.add('clicked');
                    });
                    submitButton.addEventListener('mouseup', function() {
                        setTimeout(() => {
                            this.classList.remove('clicked');
                        }, 150);
                    });
                    submitButton.addEventListener('mouseleave', function() {
                        this.classList.remove('clicked');
                    });
                }
                
                // Ensure radio buttons are clickable and functional
                function makeRadiosClickable() {
                    // Find all radio button containers
                    const radioContainers = document.querySelectorAll('.gr-radio, .gr-radio-group');
                    
                    radioContainers.forEach(function(container) {
                        const radios = container.querySelectorAll('input[type="radio"]');
                        const labels = container.querySelectorAll('label');
                        
                        radios.forEach(function(radio) {
                            // Make radio visible and clickable
                            radio.style.pointerEvents = 'auto';
                            radio.style.cursor = 'pointer';
                            radio.style.opacity = '1';
                            radio.style.zIndex = '10';
                            radio.style.position = 'relative';
                            radio.removeAttribute('disabled');
                            radio.disabled = false;
                            
                            // Find the label associated with this radio
                            let associatedLabel = null;
                            if (radio.id) {
                                associatedLabel = container.querySelector('label[for="' + radio.id + '"]');
                            }
                            if (!associatedLabel) {
                                // Try to find by position or text content
                                const radioIndex = Array.from(radios).indexOf(radio);
                                if (labels[radioIndex]) {
                                    associatedLabel = labels[radioIndex];
                                }
                            }
                            
                            // Make label clickable
                            if (associatedLabel) {
                                associatedLabel.style.pointerEvents = 'auto';
                                associatedLabel.style.cursor = 'pointer';
                                associatedLabel.style.userSelect = 'none';
                                
                                // Add click handler to label - use capture phase
                                associatedLabel.addEventListener('click', function(e) {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    
                                    // Uncheck all radios in this group first
                                    radios.forEach(function(r) {
                                        r.checked = false;
                                    });
                                    
                                    // Check this radio
                                    radio.checked = true;
                                    
                                    // Dispatch events to trigger Gradio updates
                                    const changeEvent = new Event('change', { bubbles: true, cancelable: true });
                                    radio.dispatchEvent(changeEvent);
                                    
                                    const inputEvent = new Event('input', { bubbles: true, cancelable: true });
                                    radio.dispatchEvent(inputEvent);
                                    
                                    // Also try click event
                                    radio.click();
                                    
                                    // Force visual update
                                    setTimeout(function() {
                                        radios.forEach(function(r) {
                                            const rLabel = container.querySelector('label[for="' + r.id + '"]') || 
                                                          Array.from(labels)[Array.from(radios).indexOf(r)];
                                            if (rLabel) {
                                                if (r.checked) {
                                                    rLabel.style.border = '3px solid #2563eb';
                                                    rLabel.style.background = '#eff6ff';
                                                    rLabel.style.fontWeight = '700';
                                                } else {
                                                    rLabel.style.border = '3px solid transparent';
                                                    rLabel.style.background = 'white';
                                                    rLabel.style.fontWeight = 'normal';
                                                }
                                            }
                                        });
                                    }, 10);
                                }, true); // Use capture phase
                            }
                            
                            // Ensure radio itself works
                            radio.addEventListener('click', function(e) {
                                e.stopPropagation();
                                // Update visual state after a brief delay
                                setTimeout(function() {
                                    radios.forEach(function(r) {
                                        const rLabel = container.querySelector('label[for="' + r.id + '"]') || 
                                                      Array.from(labels)[Array.from(radios).indexOf(r)];
                                        if (rLabel) {
                                            if (r.checked) {
                                                rLabel.style.border = '3px solid #2563eb';
                                                rLabel.style.background = '#eff6ff';
                                                rLabel.style.fontWeight = '700';
                                            } else {
                                                rLabel.style.border = '3px solid transparent';
                                                rLabel.style.background = 'white';
                                                rLabel.style.fontWeight = 'normal';
                                            }
                                        }
                                    });
                                }, 10);
                            });
                        });
                    });
                }
                
                // Run immediately and also after delays to catch dynamically loaded elements
                makeRadiosClickable();
                setTimeout(makeRadiosClickable, 500);
                setTimeout(makeRadiosClickable, 1000);
                setTimeout(makeRadiosClickable, 2000);
                
                // Also watch for new elements
                const observer = new MutationObserver(function(mutations) {
                    let shouldUpdate = false;
                    mutations.forEach(function(mutation) {
                        if (mutation.addedNodes.length > 0) {
                            mutation.addedNodes.forEach(function(node) {
                                if (node.nodeType === 1 && 
                                    (node.classList.contains('gr-radio') || 
                                     node.classList.contains('gr-radio-group') ||
                                     node.querySelector('.gr-radio') ||
                                     node.querySelector('.gr-radio-group'))) {
                                    shouldUpdate = true;
                                }
                            });
                        }
                    });
                    if (shouldUpdate) {
                        setTimeout(makeRadiosClickable, 100);
                    }
                });
                observer.observe(document.body, { childList: true, subtree: true });
            });
        </script>
        """
    )

    with gr.Row(elem_id="main-row"):
        with gr.Column(scale=1, elem_id="sidebar-column"):
            # Search Mode Selection
            gr.HTML(
                "<h2 style='font-size: 16px; font-weight: 600; color: #111827; margin: 0 0 12px 0;'>"
                "Search Mode</h2>"
            )
            search_type = gr.Radio(
                choices=["Search Articles", "Ask the AI"],
                value="Search Articles",
                label="Search Mode",
                info="Choose between searching for articles or asking AI questions",
                elem_classes=["custom-radio-white"]
            )

            # Common filters
            gr.HTML(
                "<h3 style='font-size: 16px; font-weight: 600; color: #111827; margin: 24px 0 12px 0;'>"
                "Filters</h3>"
            )
            query_text = gr.Textbox(label="Query", placeholder="Type your query here...", lines=3)
            
            # New AI Agent Tool filters
            gr.HTML(
                "<h4 style='font-size: 14px; font-weight: 600; color: #374151; margin: 20px 0 8px 0;'>"
                "Tool Filters</h4>"
            )
            category = gr.Dropdown(
                choices=["", "Framework", "Library", "Platform", "Tool"],
                label="Category",
                value="",
                info="Filter by tool category",
                elem_classes=["white-dropdown"]
            )
            language = gr.Dropdown(
                choices=["", "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java"],
                label="Language",
                value="",
                info="Filter by programming language",
                elem_classes=["white-dropdown"]
            )
            source_type = gr.Dropdown(
                choices=["", "github_repo", "rss_article", "documentation"],
                label="Source Type",
                value="",
                elem_classes=["white-dropdown"],
                info="Filter by source type",
            )
            min_stars = gr.Slider(
                minimum=0,
                maximum=50000,
                step=100,
                label="Min GitHub Stars",
                value=0,
                info="Filter by minimum GitHub stars (0 = no filter)",
            )
            
            # Legacy filters (kept for backward compatibility)
            gr.HTML(
                "<h4 style='font-size: 14px; font-weight: 600; color: #374151; margin: 20px 0 8px 0;'>"
                "Legacy Filters (Optional)</h4>"
            )
            feed_author = gr.Dropdown(
                choices=[""] + feed_authors, label="Author", value="",
                elem_classes=["white-dropdown"]
            )
            feed_name = gr.Dropdown(
                choices=[""] + feed_names, label="Feed", value="",
                elem_classes=["white-dropdown"]
            )

            # Conditional fields based on search type
            title_keywords = gr.Textbox(
                label="Title Keywords (optional)",
                placeholder="Filter by words in the title",
                visible=True,
            )

            limit = gr.Slider(
                minimum=1, maximum=20, step=1, label="Number of results", value=5, visible=True
            )

            # LLM Options (only visible for AI mode)
            with gr.Group(visible=False, elem_id="llm-options-group") as llm_options:
                gr.HTML(
                    "<h3 style='font-size: 16px; font-weight: 600; color: #111827; margin: 24px 0 12px 0;'>"
                    "LLM Options</h3>"
                )
                provider = gr.Dropdown(
                    choices=["OpenRouter", "HuggingFace", "OpenAI"],
                    label="Select LLM Provider",
                    value="OpenRouter",
                    elem_classes=["white-dropdown"]
                )
                model = gr.Dropdown(
                    choices=get_models_for_provider("OpenRouter"),
                    label="Select Model",
                    value="Automatic Model Selection (Model Routing)",
                    elem_classes=["white-dropdown"]
                )
                streaming_mode = gr.Radio(
                    choices=["Streaming", "Non-Streaming"],
                    value="Streaming",
                    label="Answer Mode",
                    info="Streaming shows results as they're generated",
                    elem_classes=["custom-radio-white"]
                )

            # Submit button
            submit_btn = gr.Button(
                "Search / Ask AI", 
                variant="primary", 
                size="lg",
                elem_id="submit-button"
            )

        with gr.Column(scale=2):
            # Output area
            gr.HTML(
                "<h2 style='font-size: 16px; font-weight: 600; color: #111827; margin: 0 0 16px 0;'>"
                "Results</h2>"
            )
            output_html = gr.HTML(label="", elem_classes=["results-container"])
            model_info = gr.HTML(
                visible=False,
                elem_classes=["model-info"]
            )
    
    # Event handlers
    def toggle_visibility(search_type):
        """
        Toggle visibility of components based on search type

        Args:
            search_type (str): The selected search type
        Returns:
            tuple: Visibility states for (llm_options, title_keywords, model_info)
        """

        show_title_keywords = search_type == "Search Articles"
        show_llm_options = search_type == "Ask the AI"
        show_model_info = search_type == "Ask the AI"
        show_limit_slider = search_type == "Search Articles"

        return (
            gr.Group(visible=show_llm_options),  # llm_options
            gr.Textbox(visible=show_title_keywords),  # title_keywords
            gr.HTML(visible=show_model_info),  # model_info
            gr.Slider(visible=show_limit_slider),  # limit
        )
    
    search_type.change(
        fn=toggle_visibility,
        inputs=[search_type],
        outputs=[llm_options, title_keywords, model_info, limit]
    )
    
    # Update model dropdown when provider changes
    provider.change(fn=update_model_choices, inputs=[provider], outputs=[model])
    
    # Unified submission handler
    def handle_submission(
        search_type,
        streaming_mode,
        query_text,
        feed_name,
        feed_author,
        title_keywords,
        category,
        language,
        source_type,
        min_stars,
        limit,
        provider,
        model,
    ):
        """
        Handle submission based on search type and streaming mode
        Args:
            search_type (str): The selected search type
            streaming_mode (str): The selected streaming mode
            query_text (str): The query text
            feed_name (str): The selected feed name
            feed_author (str): The selected feed author
            title_keywords (str): The title keywords (if applicable)
            category (str): Filter by category
            language (str): Filter by language
            source_type (str): Filter by source type
            min_stars (int): Filter by minimum GitHub stars
            limit (int): The number of results to return
            provider (str): The selected LLM provider (if applicable)
            model (str): The selected model (if applicable)
        Returns:
            tuple: (HTML formatted answer string, model info string)
        """
        if search_type == "Search Articles":
            result = handle_search_articles(
                query_text,
                feed_name,
                feed_author,
                title_keywords,
                category,
                language,
                source_type,
                min_stars,
                limit,
            )
            return result, ""  # Always return two values
        else:  # Ask the AI
            if streaming_mode == "Non-Streaming":
                return handle_ai_question_non_streaming(
                    query_text,
                    feed_name,
                    feed_author,
                    category,
                    language,
                    source_type,
                    min_stars,
                    limit,
                    provider,
                    model,
                )
            else:
                # For streaming, we'll use a separate handler
                return "", ""

    # Streaming handler
    def handle_streaming_submission(
        search_type,
        streaming_mode,
        query_text,
        feed_name,
        feed_author,
        title_keywords,
        category,
        language,
        source_type,
        min_stars,
        limit,
        provider,
        model,
    ):
        """
        Handle submission with streaming support
        Args:
            search_type (str): The selected search type
            streaming_mode (str): The selected streaming mode
            query_text (str): The query text
            feed_name (str): The selected feed name
            feed_author (str): The selected feed author
            title_keywords (str): The title keywords (if applicable)
            category (str): Filter by category
            language (str): Filter by language
            source_type (str): Filter by source type
            min_stars (int): Filter by minimum GitHub stars
            limit (int): The number of results to return
            provider (str): The selected LLM provider (if applicable)
            model (str): The selected model (if applicable)
        Yields:
            tuple: (HTML formatted answer string, model info string)
        """
        if search_type == "Ask the AI" and streaming_mode == "Streaming":
            yield from handle_ai_question_streaming(
                query_text,
                feed_name,
                feed_author,
                category,
                language,
                source_type,
                min_stars,
                limit,
                provider,
                model,
            )
        else:
            # For non-streaming cases, show loading message first
            if search_type == "Search Articles":
                # Show loading message
                loading_html = (
                    "<div style='background: white; border: 1px solid #e5e7eb; border-radius: 8px; "
                    "padding: 48px 24px; text-align: center;'>"
                    "<div style='display: inline-block; width: 40px; height: 40px; border: 4px solid #e5e7eb; "
                    "border-top-color: #2563eb; border-radius: 50%; animation: spin 1s linear infinite; "
                    "margin-bottom: 16px;'></div>"
                    "<h3 style='color: #374151; font-size: 18px; margin: 0; font-weight: 500;'>"
                    "<i class='fas fa-search' style='margin-right: 8px;'></i>Searching for articles...</h3>"
                    "<p style='color: #9ca3af; font-size: 14px; margin: 8px 0 0 0;'>Please wait while we find relevant results</p>"
                    "<style>"
                    "@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }"
                    "</style>"
                    "</div>"
                )
                yield loading_html, ""
                
                # Then get and return the actual results
                result = handle_search_articles(
                    query_text,
                    feed_name,
                    feed_author,
                    title_keywords,
                    category,
                    language,
                    source_type,
                    min_stars,
                    limit,
                )
                yield result, ""
            else:
                # Show loading message for non-streaming AI questions
                loading_html = (
                    "<div style='background: white; border: 1px solid #e5e7eb; border-radius: 8px; "
                    "padding: 48px 24px; text-align: center;'>"
                    "<div style='display: inline-block; width: 40px; height: 40px; border: 4px solid #e5e7eb; "
                    "border-top-color: #2563eb; border-radius: 50%; animation: spin 1s linear infinite; "
                    "margin-bottom: 16px;'></div>"
                    "<h3 style='color: #374151; font-size: 18px; margin: 0; font-weight: 500;'>"
                    "<i class='fas fa-robot' style='margin-right: 8px;'></i>Searching for relevant information...</h3>"
                    "<p style='color: #9ca3af; font-size: 14px; margin: 8px 0 0 0;'>Please wait while we generate your answer</p>"
                    "<style>"
                    "@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }"
                    "</style>"
                    "</div>"
                )
                loading_model_info = "<i class='fas fa-search' style='margin-right: 6px;'></i>Searching for relevant information..."
                yield loading_html, loading_model_info
                
                # Then get and return the actual results
                result_html, model_info_text = handle_ai_question_non_streaming(
                    query_text,
                    feed_name,
                    feed_author,
                    category,
                    language,
                    source_type,
                    min_stars,
                    limit,
                    provider,
                    model,
                )
                yield result_html, model_info_text

    # Single click handler that routes based on mode
    submit_btn.click(
        fn=handle_streaming_submission,
        inputs=[
            search_type,
            streaming_mode,
            query_text,
            feed_name,
            feed_author,
            title_keywords,
            category,
            language,
            source_type,
            min_stars,
            limit,
            provider,
            model,
        ],
        outputs=[output_html, model_info],
        show_progress=True,
    )

# For local testing
if __name__ == "__main__":
    demo.launch()
