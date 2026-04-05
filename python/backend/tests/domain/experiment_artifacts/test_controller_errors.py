"""Tests for HTTP error mapping helpers on the experiment-artifacts router."""

from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException

from domain.experiment_artifacts.controller import _raise_http_error
from domain.experiment_artifacts.error import (
    ExperimentArtifactsNotAccessibleError,
    ExperimentArtifactNotFoundError,
)


def test_raise_maps_not_accessible_to_403() -> None:
    with pytest.raises(HTTPException) as excinfo:
        _raise_http_error(ExperimentArtifactsNotAccessibleError("denied"))
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "denied"


def test_raise_maps_not_found_to_404() -> None:
    with pytest.raises(HTTPException) as excinfo:
        _raise_http_error(ExperimentArtifactNotFoundError("missing"))
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "missing"


def test_raise_maps_httpx_status_error() -> None:
    request = httpx.Request("GET", "http://example.test/x")
    response = httpx.Response(503, request=request, text="upstream")
    err = httpx.HTTPStatusError("err", request=request, response=response)
    with pytest.raises(HTTPException) as excinfo:
        _raise_http_error(err)
    assert excinfo.value.status_code == 503
    assert excinfo.value.detail == "upstream"


def test_raise_maps_httpx_request_error_to_502() -> None:
    err = httpx.RequestError("boom", request=httpx.Request("GET", "http://example.test/x"))
    with pytest.raises(HTTPException) as excinfo:
        _raise_http_error(err)
    assert excinfo.value.status_code == 502
    assert "unavailable" in str(excinfo.value.detail)


def test_raise_maps_unknown_exception_to_400() -> None:
    with pytest.raises(HTTPException) as excinfo:
        _raise_http_error(ValueError("bad input"))
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "bad input"
