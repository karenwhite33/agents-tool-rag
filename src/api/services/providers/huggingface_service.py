import re
from collections.abc import AsyncGenerator

from huggingface_hub import AsyncInferenceClient

from src.api.models.provider_models import ModelConfig
from src.api.services.providers.utils.messages import build_messages
from src.config import settings
from src.utils.logger_util import setup_logging

logger = setup_logging()

# -----------------------
# Hugging Face client
# -----------------------
hf_key = settings.hugging_face.api_key
hf_client = AsyncInferenceClient(provider="auto", api_key=hf_key)


def strip_reasoning_from_response(content: str) -> str:
    """Strip reasoning content from DeepSeek-R1 model responses.
    
    DeepSeek-R1 models output reasoning before the actual answer.
    This function detects and removes reasoning paragraphs that typically start with
    phrases like "Hmm, the user is asking..." or "Let me analyze..."
    
    Args:
        content (str): The raw response from the model.
        
    Returns:
        str: The response with reasoning stripped out.
    """
    if not content:
        return content
    
    # Try to find reasoning in tags
    # Remove <think>...</think> or <reasoning>...</reasoning> blocks
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<reasoning>.*?</reasoning>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Look for common answer markers
    answer_markers = [
        r'Final Answer:\s*(.+)',
        r'Answer:\s*(.+)',
        r'## Answer\s*(.+)',
        r'**Answer:**\s*(.+)',
    ]
    
    for marker in answer_markers:
        match = re.search(marker, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Check if content starts with or contains reasoning indicators in the first part
    content_lower = content.lower().strip()
    reasoning_indicators = [
        'hmm,',
        'hmm ',
        'let me analyze',
        'let me think',
        'let me consider',
        'i need to analyze',
        'the user is asking',
        'i will analyze',
    ]
    
    # Check first 300 characters for reasoning indicators
    first_part = content_lower[:300] if len(content_lower) > 300 else content_lower
    has_reasoning = any(indicator in first_part for indicator in reasoning_indicators)
    
    logger.info(f"Has reasoning indicators: {has_reasoning}, first part: {first_part[:100]}")
    
    if has_reasoning:
        # SIMPLE STRATEGY: If reasoning is detected, find where it ends and remove it
        # The reasoning typically ends with phrases like "comprehensive answer" or "build a comprehensive answer"
        
        # Method 1: Look for double newline (paragraph break) - reasoning is usually first paragraph
        if '\n\n' in content:
            parts = content.split('\n\n', 1)
            first_para = parts[0].strip()
            first_para_lower = first_para.lower()
            
            if any(indicator in first_para_lower for indicator in reasoning_indicators):
                logger.info(f"Removed first paragraph (reasoning): {first_para[:150]}...")
                if len(parts) > 1:
                    return parts[1].strip()
                # If only one paragraph but it's reasoning, try to find answer within it
                # Fall through to method 2
        
        # Method 2: Find the phrase that typically ends reasoning
        # Look for patterns like "...build a comprehensive answer." or "...analyze...answer."
        end_patterns = [
            r'build.*?comprehensive answer\.\s+',
            r'analyze.*?articles.*?build.*?answer\.\s+',
            r'comprehensive answer\.\s+',
            r'answer\.\s+([A-Z])',  # "answer." followed by capital letter (start of actual answer)
        ]
        
        for pattern in end_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                reasoning_end = match.end()
                # If pattern captured the next word, adjust position
                if match.groups() and match.group(1):
                    reasoning_end = match.end() - len(match.group(1))
                logger.info(f"Found reasoning end pattern at position {reasoning_end}")
                remaining = content[reasoning_end:].strip()
                if remaining:
                    return remaining
        
        # Method 3: Split by sentences and remove reasoning sentences
        # Split on period followed by space and capital letter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', content)
        
        if len(sentences) > 1:
            # Find where reasoning sentences end
            reasoning_count = 0
            for i, sentence in enumerate(sentences):
                sent_lower = sentence.lower()
                if any(indicator in sent_lower for indicator in reasoning_indicators):
                    reasoning_count += 1
                elif reasoning_count > 0:
                    # Found first non-reasoning sentence after reasoning
                    logger.info(f"Removed {reasoning_count} reasoning sentences, answer starts at sentence {i}")
                    return ' '.join(sentences[i:]).strip()
        
        # Method 4: Fallback - if content starts with reasoning, remove first 300-500 chars
        # Look for a period followed by space and capital letter (sentence boundary)
        if len(content) > 300:
            # Search for sentence boundary after position 150
            match = re.search(r'\.\s+([A-Z][a-z]{2,}\s)', content[150:500])
            if match:
                pos = match.start() + 151
                logger.info(f"Fallback: Removing first {pos} characters")
                return content[pos:].strip()
            else:
                # No clear sentence boundary, remove first 400 chars
                logger.info(f"Fallback: Removing first 400 characters")
                return content[400:].strip() if len(content) > 400 else content
    
    # Fallback: Check first paragraph for reasoning indicators
    paragraphs = content.split('\n\n')
    if paragraphs:
        first_para = paragraphs[0].strip()
        first_para_lower = first_para.lower()
        
        if any(indicator in first_para_lower for indicator in reasoning_starters):
            # First paragraph is reasoning, remove it
            if len(paragraphs) > 1:
                return '\n\n'.join(paragraphs[1:]).strip()
            else:
                # Only one paragraph, try to find where reasoning ends within it
                # Look for sentence boundary after reasoning phrase
                match = re.search(r'(let me analyze|hmm,.*?|the user is asking.*?)\.\s+([A-Z])', first_para, re.IGNORECASE)
                if match:
                    # Find position after reasoning
                    reasoning_end_pos = first_para.find(match.group(0)) + len(match.group(0)) - 1
                    return first_para[reasoning_end_pos:].strip()
    
    return content.strip()


async def generate_huggingface(prompt: str, config: ModelConfig) -> tuple[str, None]:
    """Generate a response from Hugging Face for a given prompt and model configuration.

    Args:
        prompt (str): The input prompt.
        config (ModelConfig): The model configuration.

    Returns:
        tuple[str, None]: The generated response and None for model and finish reason.

    """
    resp = await hf_client.chat.completions.create(
        model=config.primary_model,
        messages=build_messages(prompt),
        temperature=config.temperature,
        max_tokens=config.max_completion_tokens,
    )
    raw_content = resp.choices[0].message.content or ""
    logger.info(f"Raw HuggingFace response length: {len(raw_content)}")
    logger.info(f"Raw HuggingFace response first 200 chars: {raw_content[:200]}")
    # Strip reasoning from DeepSeek-R1 responses
    cleaned_content = strip_reasoning_from_response(raw_content)
    logger.info(f"Cleaned HuggingFace response length: {len(cleaned_content)}")
    logger.info(f"Cleaned HuggingFace response first 200 chars: {cleaned_content[:200]}")
    return cleaned_content, None


def stream_huggingface(prompt: str, config: ModelConfig) -> AsyncGenerator[str, None]:
    """Stream a response from Hugging Face for a given prompt and model configuration.

    Args:
        prompt (str): The input prompt.
        config (ModelConfig): The model configuration.

    Returns:
        AsyncGenerator[str, None]: An asynchronous generator yielding response chunks.

    """

    async def gen() -> AsyncGenerator[str, None]:
        buffer = []  # Buffer ALL chunks until we confirm reasoning is past
        answer_started = False
        reasoning_detected = False
        
        stream = await hf_client.chat.completions.create(
            model=config.primary_model,
            messages=build_messages(prompt),
            temperature=config.temperature,
            max_tokens=config.max_completion_tokens,
            stream=True,
        )
        
        async for chunk in stream:
            delta_text = getattr(chunk.choices[0].delta, "content", None)
            if delta_text:
                # Always buffer first
                buffer.append(delta_text)
                current_text = "".join(buffer)
                current_lower = current_text.lower()
                
                # Check if we've detected reasoning in the buffer
                if not reasoning_detected:
                    # Check first 200 chars for reasoning indicators
                    first_part = current_lower[:200] if len(current_lower) > 200 else current_lower
                    if any(ind in first_part for ind in ['hmm,', 'hmm ', 'let me analyze', 'the user is asking']):
                        reasoning_detected = True
                        logger.info(f"Streaming: Reasoning detected in buffer (first 200 chars: {current_text[:200]})")
                
                # If reasoning is detected, we need to find where it ends
                if reasoning_detected and not answer_started:
                    # Look for "comprehensive answer." - this is the key phrase that ends reasoning
                    # Try multiple patterns to catch variations
                    patterns_to_try = [
                        r'comprehensive answer\.\s*',  # "comprehensive answer."
                        r'comprehensive answer\.',     # "comprehensive answer." (no space after)
                        r'build.*?comprehensive answer\.\s*',  # "build a comprehensive answer."
                    ]
                    
                    for pattern in patterns_to_try:
                        match = re.search(pattern, current_text, re.IGNORECASE)
                        if match:
                            # Found the end of reasoning!
                            answer_started = True
                            reasoning_end = match.end()
                            remaining = current_text[reasoning_end:].strip()
                            logger.info(f"Streaming: Found 'comprehensive answer' at position {reasoning_end}, remaining length: {len(remaining)}")
                            if remaining:
                                # Yield the remaining text from buffer
                                yield remaining
                            # Clear buffer since we've yielded what we need
                            buffer = []
                            break
                    
                    # If we haven't found the end yet, keep buffering
                    # But if buffer gets very large, use fallback
                    if not answer_started and len(current_text) > 800:
                        # Buffer is large, try to find any sentence boundary after reasoning
                        # Look for period + space + capital letter after position 200
                        match = re.search(r'\.\s+([A-Z][a-z]{3,})', current_text[200:])
                        if match:
                            pos = match.start() + 201
                            answer_started = True
                            remaining = current_text[pos:].strip()
                            logger.info(f"Streaming: Fallback - using sentence boundary at position {pos}")
                            if remaining:
                                yield remaining
                            buffer = []
                        else:
                            # Last resort: remove first 400 chars
                            answer_started = True
                            remaining = current_text[400:].strip()
                            logger.info(f"Streaming: Last resort - removing first 400 chars")
                            if remaining:
                                yield remaining
                            buffer = []
                
                # If answer has started, yield new chunks immediately
                elif answer_started:
                    yield delta_text
                
                # If no reasoning detected and buffer is reasonably large, start yielding
                elif not reasoning_detected and len(current_text) > 100:
                    # No reasoning detected, safe to yield
                    answer_started = True
                    # Yield what we've buffered so far
                    if current_text:
                        yield current_text
                    buffer = []
        
        # Final check: if we never started answering but have buffer, post-process it
        if not answer_started and buffer:
            full_response = "".join(buffer)
            cleaned = strip_reasoning_from_response(full_response)
            logger.info(f"Streaming: Final fallback - post-processing {len(full_response)} chars")
            if cleaned and cleaned != full_response:
                yield cleaned
            elif cleaned:
                yield cleaned
        
    return gen()
