"""
LLM service for the AJU RAG system.

Isolates all provider-specific OpenRouter/OpenAI-compatible API logic behind a
generic interface so the rest of the system is not coupled to a particular
streaming implementation.

Public interface:
  complete_chat(messages, model, temperature) -> ChatResult
  stream_chat(messages, model, temperature)   -> AsyncGenerator[StreamEvent, None]
"""
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))


# ---------------------------------------------------------------------------
# Result & Event types
# ---------------------------------------------------------------------------

@dataclass
class ChatResult:
    answer: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    llm_latency_ms: float = 0.0


@dataclass
class StreamEvent:
    event_type: str       # "token" | "error" | "done" | "first_token"
    text: str = ""
    error_detail: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    llm_latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Provider client (private, instantiated once per module)
# ---------------------------------------------------------------------------

def _make_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        timeout=LLM_TIMEOUT,
        default_headers={
            "HTTP-Referer": "https://arthurjarvisuniversity.edu.ng",
            "X-Title": "AJU Knowledge Management Platform",
        },
    )


_client: Optional[AsyncOpenAI] = None


def get_llm_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = _make_client()
    return _client


# ---------------------------------------------------------------------------
# Non-streaming completion
# ---------------------------------------------------------------------------

async def complete_chat(
    messages: List[Dict[str, str]],
    model: str = LLM_MODEL,
    temperature: float = 0.2,
) -> ChatResult:
    """
    Send messages to the LLM and return the full response.
    Handles timeouts, rate limits, and connection errors gracefully.
    """
    client = get_llm_client()
    t0 = time.perf_counter()

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        answer = completion.choices[0].message.content or ""
        usage = completion.usage
        return ChatResult(
            answer=answer,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            llm_latency_ms=elapsed_ms,
        )

    except APITimeoutError:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.error("LLM request timed out after %.1f ms", elapsed_ms)
        raise

    except APIStatusError as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if exc.status_code == 429:
            logger.warning("LLM rate limit hit (429) after %.1f ms", elapsed_ms)
        else:
            logger.error("LLM API error %d after %.1f ms", exc.status_code, elapsed_ms)
        raise

    except APIConnectionError:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.error("LLM connection error after %.1f ms", elapsed_ms)
        raise

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.error("Unexpected LLM error after %.1f ms: %s", elapsed_ms, exc)
        raise


# ---------------------------------------------------------------------------
# Streaming completion
# ---------------------------------------------------------------------------

async def stream_chat(
    messages: List[Dict[str, str]],
    model: str = LLM_MODEL,
    temperature: float = 0.2,
) -> AsyncGenerator[StreamEvent, None]:
    """
    Stream LLM tokens as StreamEvent objects.

    Yields:
      StreamEvent(event_type="first_token", ...) — on first token (latency measurement)
      StreamEvent(event_type="token", text=<chunk>) — for each text token
      StreamEvent(event_type="done", llm_latency_ms=..., prompt_tokens=..., completion_tokens=...)
      StreamEvent(event_type="error", error_detail=...) — on any failure
    """
    client = get_llm_client()
    t0 = time.perf_counter()
    first_token = True
    total_text = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                text = delta.content
                total_text += text
                elapsed_ms = (time.perf_counter() - t0) * 1000

                if first_token:
                    first_token = False
                    yield StreamEvent(
                        event_type="first_token",
                        text=text,
                        llm_latency_ms=elapsed_ms,
                    )
                else:
                    yield StreamEvent(event_type="token", text=text)

            # Capture usage from final chunk (OpenAI sends it in the last chunk)
            if hasattr(chunk, "usage") and chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens

        total_elapsed_ms = (time.perf_counter() - t0) * 1000
        yield StreamEvent(
            event_type="done",
            llm_latency_ms=total_elapsed_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    except APITimeoutError:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.error("LLM stream timed out after %.1f ms", elapsed_ms)
        yield StreamEvent(event_type="error", error_detail="LLM request timed out.")

    except APIStatusError as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if exc.status_code == 429:
            logger.warning("LLM rate limit hit (429) after %.1f ms", elapsed_ms)
            yield StreamEvent(event_type="error", error_detail="LLM rate limit exceeded. Please retry shortly.")
        else:
            logger.error("LLM API error %d: %s", exc.status_code, exc.message)
            yield StreamEvent(event_type="error", error_detail="LLM provider error.")

    except APIConnectionError:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.error("LLM stream connection error after %.1f ms", elapsed_ms)
        yield StreamEvent(event_type="error", error_detail="LLM connection failed.")

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.error("Unexpected LLM stream error after %.1f ms: %s", elapsed_ms, exc)
        yield StreamEvent(event_type="error", error_detail="Unexpected error during response generation.")
