"""
core/llm.py — Streaming LLM via Ollama (OpenAI-compatible API).
Provides streaming chat completions with sentence-level buffering for TTS.
"""

import re
from openai import OpenAI
from config import LLM_MODEL, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_SYSTEM_PROMPT
from logger import setup_logging

logger = setup_logging()

# ── Client Setup ─────────────────────────────────────────────
_client = None


def _get_client():
    """Lazy-initialize the OpenAI client pointing at Ollama."""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=LLM_BASE_URL,
            api_key="ollama",  # Required by SDK but ignored by Ollama
        )
    return _client


def is_ollama_available():
    """Check if Ollama is reachable."""
    try:
        client = _get_client()
        client.models.list()
        return True
    except Exception:
        return False


# ── Streaming Chat ───────────────────────────────────────────

def stream_chat(messages, on_sentence=None):
    """
    Send messages to Ollama and stream the response.

    Args:
        messages: List of {"role": ..., "content": ...} dicts.
                  System prompt is prepended automatically.
        on_sentence: Optional callback(sentence_str) called each time
                     a complete sentence is detected (for streaming TTS).

    Returns:
        The full response text.
    """
    client = _get_client()

    # Prepend system prompt — add /no_think to suppress qwen reasoning blocks
    system_content = LLM_SYSTEM_PROMPT + "\n\n/no_think"
    full_messages = [{"role": "system", "content": system_content}] + messages

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=full_messages,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            stream=True,
        )

        full_text = ""
        sentence_buffer = ""
        in_think_block = False  # Track <think> blocks from qwen models

        for chunk in response:
            token = chunk.choices[0].delta.content
            if not token:
                continue

            # Handle qwen <think>...</think> blocks — skip them entirely
            if "<think>" in token:
                in_think_block = True
                # Remove any text before <think> that we should keep
                before = token.split("<think>")[0]
                if before.strip():
                    full_text += before
                    sentence_buffer += before
                continue
            if "</think>" in token:
                in_think_block = False
                # Keep any text after </think>
                after = token.split("</think>")[-1]
                if after.strip():
                    full_text += after
                    sentence_buffer += after
                continue
            if in_think_block:
                continue  # Skip thinking content

            full_text += token
            sentence_buffer += token

            # Check for sentence boundaries and fire TTS callback
            if on_sentence and re.search(r'[.!?]\s*$', sentence_buffer):
                sentences = _split_sentences(sentence_buffer)

                if len(sentences) > 1:
                    for s in sentences[:-1]:
                        s = s.strip()
                        if s:
                            on_sentence(s)
                    sentence_buffer = sentences[-1]
                elif len(sentences) == 1:
                    s = sentences[0].strip()
                    if s:
                        on_sentence(s)
                    sentence_buffer = ""

        # Speak any remaining text
        if on_sentence and sentence_buffer.strip():
            on_sentence(sentence_buffer.strip())

        # Clean up any stray think tags from the final text
        full_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL).strip()

        return full_text

    except Exception as e:
        logger.error(f"LLM streaming error: {e}")
        return _fallback_response(messages[-1]["content"] if messages else "")


def chat(messages):
    """Non-streaming chat — returns the full response at once."""
    return stream_chat(messages, on_sentence=None)


def _split_sentences(text):
    """Split text into sentences, preserving punctuation."""
    # Split on sentence-ending punctuation followed by space or end of string
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p for p in parts if p]


def _fallback_response(user_input):
    """Fallback responses when Ollama is unreachable."""
    user_input = user_input.lower()

    if "hello" in user_input or "hi" in user_input:
        return "Hello. Ollama appears to be offline, so I'm running with limited intelligence. I can still handle system commands."
    elif "time" in user_input:
        from datetime import datetime
        return f"It's {datetime.now().strftime('%I:%M %p')}."
    elif "date" in user_input:
        from datetime import datetime
        return f"Today is {datetime.now().strftime('%B %d, %Y')}."
    else:
        return "My brain is offline — Ollama isn't responding. I can still run system commands though. Try 'open Chrome' or 'take a screenshot'."
