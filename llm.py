import asyncio
from typing import Any

import weave
from anthropic import AsyncAnthropic, RateLimitError
from pydantic import BaseModel, ValidationError

_client = AsyncAnthropic()
_MAX_ATTEMPTS = 3
_RETRY_STOP_REASONS = frozenset({"max_tokens", "refusal"})
_RATE_LIMIT_RETRIES = 5


async def _with_rate_limit_retry(coro_factory):
    for attempt in range(_RATE_LIMIT_RETRIES):
        try:
            return await coro_factory()
        except RateLimitError:
            if attempt == _RATE_LIMIT_RETRIES - 1:
                raise
            await asyncio.sleep(2 ** attempt * 5)


def _supports_parse() -> bool:
    return hasattr(_client.messages, "parse")


def _extract_message_text(content: Any) -> str:
    parts: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text" and getattr(block, "text", None):
            parts.append(block.text)
    return "\n".join(parts)


async def _call_parse(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    schema: type[BaseModel],
    max_tokens: int,
    tools: list[Any] | None,
) -> tuple[BaseModel, str | None]:
    kwargs: dict[str, Any] = {}
    if tools is not None:
        kwargs["tools"] = tools

    resp = await _with_rate_limit_retry(
        lambda: _client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_format=schema,
            **kwargs,
        )
    )
    if resp.parsed_output is None:
        raise ValidationError.from_exception_data(
            schema.__name__,
            [{"type": "missing", "loc": (), "msg": "parsed_output was empty"}],
        )
    return resp.parsed_output, resp.stop_reason


async def _call_create_fallback(
    model: str,
    system: str,
    messages: list[dict[str, str]],
    schema: type[BaseModel],
    max_tokens: int,
    tools: list[Any] | None,
) -> tuple[BaseModel, str | None]:
    kwargs: dict[str, Any] = {}
    if tools is not None:
        kwargs["tools"] = tools

    resp = await _with_rate_limit_retry(
        lambda: _client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config={
                "format": {"type": "json_schema", "schema": schema.model_json_schema()}
            },
            **kwargs,
        )
    )
    result = schema.model_validate_json(resp.content[0].text)
    return result, resp.stop_reason


async def _call_search_then_format(
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    max_tokens: int,
    tools: list[Any],
) -> BaseModel:
    search_system = (
        system
        + "\n\nUse web search when helpful. After searching, summarize every fact you "
        "will cite in the final structured report."
    )
    resp = await _with_rate_limit_retry(
        lambda: _client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=search_system,
            messages=[{"role": "user", "content": user}],
            tools=tools,
        )
    )
    gathered = _extract_message_text(resp.content)
    format_messages = [
        {
            "role": "user",
            "content": (
                "Original task context:\n"
                f"{user}\n\n"
                "Research gathered (including web search results):\n"
                f"{gathered}\n\n"
                "Produce the structured JSON report now. Use evidence_citations with the "
                "required prefixes (deck:, web:, YC:)."
            ),
        }
    ]
    result, stop_reason = await _call_parse(
        model, system, format_messages, schema, max_tokens, None
    )
    if stop_reason == "refusal":
        raise RuntimeError("Model refused to produce structured output")
    return result


async def _structured_with_tools(
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    max_tokens: int,
    tools: list[Any],
) -> BaseModel:
    messages = [{"role": "user", "content": user}]
    try:
        if _supports_parse():
            result, stop_reason = await _call_parse(
                model, system, messages, schema, max_tokens, tools
            )
        else:
            result, stop_reason = await _call_create_fallback(
                model, system, messages, schema, max_tokens, tools
            )
        if stop_reason in _RETRY_STOP_REASONS and stop_reason == "refusal":
            raise RuntimeError("Model refused to produce structured output")
        return result
    except (ValidationError, TypeError, AttributeError, IndexError, KeyError):
        return await _call_search_then_format(
            model, system, user, schema, max_tokens, tools
        )
    except Exception as exc:
        if "authentication" in str(exc).lower() or "api_key" in str(exc).lower():
            raise
        return await _call_search_then_format(
            model, system, user, schema, max_tokens, tools
        )


@weave.op
async def structured(
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    tools: list[Any] | None = None,
    max_tokens: int = 2048,
) -> BaseModel:
    if tools:
        return await _structured_with_tools(
            model, system, user, schema, max_tokens, tools
        )

    messages = [{"role": "user", "content": user}]
    tokens = max_tokens
    last_validation_error: ValidationError | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            if _supports_parse():
                result, stop_reason = await _call_parse(
                    model, system, messages, schema, tokens, None
                )
            else:
                result, stop_reason = await _call_create_fallback(
                    model, system, messages, schema, tokens, None
                )
        except ValidationError as exc:
            last_validation_error = exc
            continue

        if stop_reason not in _RETRY_STOP_REASONS:
            return result

        if stop_reason == "max_tokens":
            tokens *= 2
            continue

        if stop_reason == "refusal" and attempt == _MAX_ATTEMPTS - 1:
            raise RuntimeError("Model refused to produce structured output")

    if last_validation_error is not None:
        raise last_validation_error
    raise RuntimeError("structured output failed after retries")
