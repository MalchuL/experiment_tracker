"""Every test in this package runs under the session ``isolated_test_environment``."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures("isolated_test_environment")
