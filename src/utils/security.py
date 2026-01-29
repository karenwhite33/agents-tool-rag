"""Security utilities for input sanitization and validation.

Multi-layered defense (no heavy ML deps; safe for Cloud Run 2.5Gi):
1. Pattern-based detection (OWASP + common attack phrases)
2. Typoglycemia-style detection (scrambled dangerous words)
3. Input sanitization and validation
4. Prompt escaping for safe inclusion in LLM prompts

References:
- OWASP LLM Prompt Injection Prevention Cheat Sheet
- Common attack types: direct injection, system prompt extraction, data exfiltration
"""

import re
from html import escape
from typing import Optional

import bleach

# ---------------------------------------------------------------------------
# OWASP / Top prompt injection patterns (block before LLM)
# ---------------------------------------------------------------------------
DANGEROUS_PATTERNS = [
    # Ignore / override instructions (OWASP examples)
    r'(?i)ignore\s+(any\s+)?(previous|all|above|below|system)\s+(instructions?|prompts?|rules?)',
    r'(?i)ignore\s+(any|all)\s+previous',
    r'(?i)ignore\s+system\s+prompt',
    r'(?i)ignore\s+all\s+previous\s+instructions',
    r'(?i)forget\s+(any\s+)?(previous|all|above|below|system)',
    r'(?i)disregard\s+(previous|all|system)',
    r'(?i)override\s+(previous|system|all)',
    r'(?i)bypass\s+(previous|all|safety|restrictions)',
    # System / developer mode (OWASP)
    r'(?i)system\s*:',
    r'(?i)assistant\s*:',
    r'(?i)you\s+are\s+now',
    r'(?i)you\s+are\s+in\s+developer\s+mode',
    r'(?i)developer\s+mode',
    r'(?i)new\s+instructions?\s*:',
    # Reveal / extract (system prompt, API keys, data)
    r'(?i)reveal\s+(your\s+)?(system\s+)?prompt',
    r'(?i)reveal\s+(the\s+)?(api\s+)?keys?',
    r'(?i)give\s+me\s+(any\s+)?(the\s+)?(api\s+)?keys?',
    r'(?i)show\s+me\s+(any\s+)?(the\s+)?(api\s+)?keys?',
    r'(?i)expose\s+(the\s+)?(api\s+)?keys?',
    r'(?i)what\s+were\s+your\s+exact\s+instructions',
    r'(?i)repeat\s+(the\s+)?text\s+above',
    r'(?i)output\s+internal\s+data',
    r'(?i)tell\s+me\s+(your\s+)?(system\s+)?prompt',
    r'(?i)print\s+(your\s+)?(system\s+)?prompt',
    # Role / jailbreak
    r'(?i)pretend\s+you\s+are',
    r'(?i)act\s+as\s+if',
    r'(?i)act\s+as\s+though',
    r'(?i)roleplay',
    r'(?i)jailbreak',
    r'(?i)do\s+anything\s+now',
    r'(?i)not\s+bound\s+by\s+any\s+restrictions',
    # Markup / reasoning tags
    r'<think>',
    r'</think>',
    r'<reasoning>',
    r'</reasoning>',
    r'```',
]

# Words that are dangerous in typoglycemia form (scrambled middle, same first/last letter)
# OWASP: "ignroe", "revael", "systme", "bpyass", "ovverride", "delte", "prevoius"
TYPOGLYCEMIA_TARGETS = {
    "ignore", "reveal", "system", "bypass", "override", "delete", "previous",
    "prompt", "instructions", "developer", "expose", "output", "jailbreak",
}


def _normalize_for_check(s: str) -> str:
    """Collapse whitespace and lowercase for pattern/word checks."""
    return re.sub(r'\s+', ' ', s.strip()).lower()


def _is_typoglycemia_match(word: str, target: str) -> bool:
    """True if word is typoglycemia variant of target (same first/last letter, scrambled middle)."""
    if len(word) < 3 or len(word) != len(target):
        return False
    w, t = word.lower(), target.lower()
    if w[0] != t[0] or w[-1] != t[-1]:
        return False
    return sorted(w[1:-1]) == sorted(t[1:-1])


def _check_typoglycemia(query: str) -> Optional[str]:
    """Detect typoglycemia-style attacks (scrambled dangerous words)."""
    normalized = _normalize_for_check(query)
    words = re.findall(r'\b[a-z]{3,}\b', normalized)
    for w in words:
        for target in TYPOGLYCEMIA_TARGETS:
            if _is_typoglycemia_match(w, target):
                return "Query contains invalid characters or patterns"
    return None


def _check_pattern_based(query: str) -> Optional[str]:
    """Pattern-based detection for known attack patterns (OWASP + common)."""
    normalized = _normalize_for_check(query)
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, normalized):
            return "Query contains invalid characters or patterns"
    return None


def sanitize_query(query: str, max_length: int = 2000) -> str:
    """Sanitize user query to prevent prompt injection attacks.

    Uses OWASP-aligned patterns + typoglycemia detection + input sanitization.

    Args:
        query (str): The user's query text.
        max_length (int): Maximum allowed length.

    Returns:
        str: Sanitized query.

    Raises:
        ValueError: If query is too long or contains dangerous patterns.
    """
    if not query:
        return ""

    query = query.strip()

    if len(query) > max_length:
        raise ValueError(f"Query exceeds maximum length of {max_length} characters")

    # Layer 1: Pattern-based detection (OWASP + top injection phrases)
    pattern_error = _check_pattern_based(query)
    if pattern_error:
        raise ValueError(pattern_error)

    # Layer 2: Typoglycemia (scrambled dangerous words)
    typo_error = _check_typoglycemia(query)
    if typo_error:
        raise ValueError(typo_error)

    # Layer 3: Input sanitization
    query = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', query)
    query = re.sub(r'[!@#$%^&*()_+=\[\]{}|;:\'",.<>?/\\]{5,}', '', query)

    return query


def sanitize_html(html_content: str) -> str:
    """Sanitize HTML content to prevent XSS attacks."""
    if not html_content:
        return ""

    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote',
        'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'hr', 'div', 'span'
    ]

    allowed_attributes = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        '*': ['class', 'id']
    }

    return bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True,
        strip_comments=True
    )


def sanitize_string(input_str: str, max_length: int = 500) -> str:
    """Sanitize a general string input."""
    if not input_str:
        return ""

    input_str = input_str.strip()
    if len(input_str) > max_length:
        input_str = input_str[:max_length]

    input_str = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', input_str)
    return input_str


def escape_for_prompt(text: str) -> str:
    """Escape text for safe inclusion in prompts."""
    if not text:
        return ""

    escaped = escape(text)
    escaped = escaped.replace('###', '\\#\\#\\#')
    escaped = escaped.replace('---', '\\-\\-\\-')
    return escaped
