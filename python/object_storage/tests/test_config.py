from __future__ import annotations

import pytest

from object_storage.config import get_settings


def test_env_vars_override_defaults_for_testcontainers(
    pytestconfig: pytest.Config,
) -> None:
    settings = get_settings()

    expected_database_url = pytestconfig.cache.get("object_storage/test_database_url", "")
    expected_s3_endpoint = pytestconfig.cache.get(
        "object_storage/test_s3_endpoint_url", ""
    )
    assert expected_database_url
    assert expected_s3_endpoint
    assert settings.database_url == expected_database_url
    assert settings.storage_backend == "s3"
    assert settings.s3_endpoint_url == expected_s3_endpoint
    assert settings.s3_access_key_id == "admin"
    assert settings.s3_secret_access_key == "password"
    assert settings.s3_bucket == "ml-blobs-test"
