"""
core/llm.py — Tool-calling LLM agent via Ollama (qwen:7b compatible).

Architecture (prompt-based JSON dispatch, works with any model):
  1. Build a system prompt listing all available tools + JSON call format
  2. Stream LLM response, scan for JSON tool calls
  3. Execute tools, inject results back, get verbal confirmation response
  4. Stream that confirmation into TTS pipeline
"""

import re
import json
import threading
from openai import OpenAI
from config import LLM_MODEL, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_SYSTEM_PROMPT
from logger import setup_logging

logger = setup_logging()

# ── Client ────────────────────────────────────────────────────
_client = None
_llm_interrupt_event = threading.Event()


def stop():
    """Interrupt the current LLM stream."""
    _llm_interrupt_event.set()


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(base_url=LLM_BASE_URL, api_key="ollama")
    return _client


def is_ollama_available():
    try:
        client = _get_client()
        client.models.list()

        def _warmup():
            try:
                client.chat.completions.create(
                    model=LLM_MODEL, messages=[{"role": "user", "content": "hi"}], max_tokens=1
                )
            except Exception:
                pass

        threading.Thread(target=_warmup, daemon=True).start()
        return True
    except Exception:
        return False


# ── Tool prompt builder ───────────────────────────────────────

def _build_tools_system_prompt(base_prompt):
    """Inject tool descriptions into system prompt for prompt-based dispatch."""
    from tools.registry import registry
    if not registry.tools:
        return base_prompt

    tool_list = []
    for t in registry.tools:
        fn = t["function"]
        name = fn["name"]
        desc = fn["description"]
        props = fn.get("parameters", {}).get("properties", {})
        params_str = ", ".join(
            f'{k} ({v.get("type", "string")}): {v.get("description", "")}' 
            for k, v in props.items()
        )
        tool_list.append(f'  - {name}({params_str}): {desc}')

    tools_block = "\n".join(tool_list)

    return (
        base_prompt.strip()
        + "\n\n"
        + "## Tools\n"
        + "You have access to these tools. To call a tool, output EXACTLY this JSON on its own line with no extra text:\n"
        + '{"tool": "tool_name", "args": {"param": "value"}}\n'
        + "After calling a tool, give a SHORT one-sentence spoken confirmation.\n"
        + "Only call tools when the user's request requires an action. For questions, answer directly.\n\n"
        + "Available tools:\n"
        + tools_block
        + "\n\n/no_think"
    )


# ── Tool call detection ───────────────────────────────────────

_TOOL_JSON_PATTERN = re.compile(
    r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^{}]*\}[^{}]*\}',
    re.DOTALL
)


def _extract_tool_call(text):
    """Extract the first JSON tool call from a text block. Returns (name, args) or None."""
    match = _TOOL_JSON_PATTERN.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        name = data.get("tool")
        args = data.get("args", {})
        if name:
            return name, args
    except json.JSONDecodeError:
        pass
    return None


def _execute_tool(name, args):
    """Execute a named tool and return its string result."""
    from tools.registry import registry
    logger.info(f"Tool call: {name}({args})")
    return registry.execute(name, args)


# ── Main streaming chat ───────────────────────────────────────

def stream_chat(messages, on_sentence=None):
    """
    Stream response from qwen:7b with prompt-based tool dispatch.

    Flow:
      Stream tokens → buffer until tool JSON detected or sentence complete
      If tool JSON found → execute tool → second LLM call for verbal response
      Else → pipe streamed tokens directly into TTS via on_sentence()
    """
    client = _get_client()

    system_content = _build_tools_system_prompt(LLM_SYSTEM_PROMPT)
    full_messages = [{"role": "system", "content": system_content}] + list(messages)

    try:
        from core import tts
        tts._tts_stop_event.clear()
        _llm_interrupt_event.clear()

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=full_messages,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            stream=True,
        )

        full_text = ""
        sentence_buffer = ""
        in_think_block = False
        tool_fired = False

        for chunk in response:
            if _llm_interrupt_event.is_set():
                break

            token = chunk.choices[0].delta.content
            if not token:
                continue

            # Strip <think> blocks
            if "<think>" in token:
                in_think_block = True
                continue
            if "</think>" in token:
                in_think_block = False
                continue
            if in_think_block:
                continue

            full_text += token
            sentence_buffer += token

            # Check for embedded tool call JSON
            tool_call = _extract_tool_call(full_text)
            if tool_call and not tool_fired:
                tool_fired = True
                tool_name, tool_args = tool_call

                # Execute the tool
                tool_result = _execute_tool(tool_name, tool_args)

                # Speak immediate feedback 
                if on_sentence:
                    on_sentence(tool_result[:160])

                # Second LLM call: short verbal confirmation
                if not _llm_interrupt_event.is_set():
                    confirm_messages = full_messages + [
                        {"role": "assistant", "content": full_text},
                        {"role": "user", "content": f"[Tool result: {tool_result}] Give a single spoken sentence confirming what you just did."},
                    ]
                    try:
                        confirm_resp = client.chat.completions.create(
                            model=LLM_MODEL,
                            messages=confirm_messages,
                            max_tokens=60,
                            temperature=0.3,
                            stream=True,
                        )
                        confirm_text = ""
                        confirm_buf = ""
                        in_think2 = False
                        for c2 in confirm_resp:
                            if _llm_interrupt_event.is_set():
                                break
                            t2 = c2.choices[0].delta.content
                            if not t2:
                                continue
                            if "<think>" in t2:
                                in_think2 = True
                                continue
                            if "</think>" in t2:
                                in_think2 = False
                                continue
                            if in_think2:
                                continue
                            confirm_text += t2
                            confirm_buf += t2
                            if on_sentence and re.search(r'[.!?]\s*$', confirm_buf):
                                s = confirm_buf.strip()
                                if s:
                                    on_sentence(s)
                                confirm_buf = ""
                        if on_sentence and confirm_buf.strip():
                            on_sentence(confirm_buf.strip())
                        return confirm_text.strip() or tool_result
                    except Exception as e:
                        logger.warning(f"Confirm call failed: {e}")
                return tool_result

            # No tool call yet — pipe sentences into TTS
            if not tool_fired and on_sentence and re.search(r'[,.!?]\s*$', sentence_buffer):
                sentences = _split_sentences(sentence_buffer)
                if len(sentences) > 1:
                    for s in sentences[:-1]:
                        s = s.strip()
                        if s and not _TOOL_JSON_PATTERN.search(s):
                            on_sentence(s)
                    sentence_buffer = sentences[-1]
                elif sentences:
                    s = sentences[0].strip()
                    if s and not _TOOL_JSON_PATTERN.search(s):
                        on_sentence(s)
                    sentence_buffer = ""

        # Flush remaining buffer (if no tool called)
        if not tool_fired:
            remaining = sentence_buffer.strip()
            if on_sentence and remaining and not _TOOL_JSON_PATTERN.search(remaining):
                on_sentence(remaining)

        full_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL).strip()
        # Strip any raw tool JSON from spoken text
        full_text = _TOOL_JSON_PATTERN.sub('', full_text).strip()
        return full_text

    except Exception as e:
        logger.error(f"LLM error: {e}")
        return _fallback_response(messages[-1]["content"] if messages else "")


def chat(messages):
    """Non-streaming chat."""
    return stream_chat(messages, on_sentence=None)


def _split_sentences(text):
    parts = re.split(r'(?<=[,.!?])\s+', text)
    return [p for p in parts if p]


def _fallback_response(user_input):
    user_input = user_input.lower()
    if any(w in user_input for w in ["hello", "hi", "hey"]):
        return "Hello. Ollama is offline — system commands still work."
    elif "time" in user_input:
        from datetime import datetime
        return f"It's {datetime.now().strftime('%I:%M %p')}."
    elif "date" in user_input:
        from datetime import datetime
        return f"Today is {datetime.now().strftime('%B %d, %Y')}."
    return "My brain is offline — Ollama isn't responding."
