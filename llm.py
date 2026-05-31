from typing import Any

import weave
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

_client = AsyncAnthropic()
_MAX_ATTEMPTS = 3
_RETRY_STOP_REASONS = frozenset({"max_tokens", "refusal"})


def _supports_parse() -> bool:
    return hasattr(_client.messages, "parse")


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

    resp = await _client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        output_format=schema,
        **kwargs,
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

    resp = await _client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        output_config={
            "format": {"type": "json_schema", "schema": schema.model_json_schema()}
        },
        **kwargs,
    )
    result = schema.model_validate_json(resp.content[0].text)
    return result, resp.stop_reason


@weave.op
async def structured(
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    tools: list[Any] | None = None,
    max_tokens: int = 2048,
) -> BaseModel:
    messages = [{"role": "user", "content": user}]
    tokens = max_tokens
    last_validation_error: ValidationError | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            if _supports_parse():
                result, stop_reason = await _call_parse(
                    model, system, messages, schema, tokens, tools
                )
            else:
                result, stop_reason = await _call_create_fallback(
                    model, system, messages, schema, tokens, tools
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
