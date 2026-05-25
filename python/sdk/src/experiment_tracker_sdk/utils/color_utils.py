from __future__ import annotations

import random


def random_hex_color() -> str:
    """Return a random 6-digit hex color string (e.g. ``#a1b2c3``)."""
    return f"#{random.randint(0, 16777215):06x}"
