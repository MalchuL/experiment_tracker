from __future__ import annotations

from typing import Any

import msgpack  # type: ignore
from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError


def _accepts_msgpack(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/msgpack" in accept.lower()


def _is_msgpack_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    return content_type.lower().startswith("application/msgpack")


async def parse_request_model(request: Request, model: type[BaseModel]) -> BaseModel:
    if _is_msgpack_request(request):
        raw = await request.body()
        data = msgpack.unpackb(raw or b"", raw=False)
    else:
        data = await request.json()
    try:
        return model.model_validate(data)
    except ValidationError as exc:  # pragma: no cover - error passthrough
        raise RequestValidationError(exc.errors()) from exc


def pack_response(request: Request, payload: Any) -> Any | Response:
    if not _accepts_msgpack(request):
        return payload
    encoded = jsonable_encoder(payload)
    packed = msgpack.packb(encoded, use_bin_type=True)
    return Response(content=packed, media_type="application/msgpack")
