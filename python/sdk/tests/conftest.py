import pytest


@pytest.fixture(autouse=True)
def _reset_exp_tracker_settings_cache() -> None:
    """Settings are cached; clear between tests so env changes stay isolated."""
    from experiment_tracker_sdk.settings import get_exp_tracker_settings

    get_exp_tracker_settings.cache_clear()
    yield
    get_exp_tracker_settings.cache_clear()
