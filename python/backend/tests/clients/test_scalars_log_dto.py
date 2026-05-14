import pytest

from clients.scalars.dto import LogScalarRequestDTO


def test_log_scalar_accepts_long_metric_name_key() -> None:
    key = "m" * 2000
    dto = LogScalarRequestDTO(scalars={key: 1.0}, step=0, tags=None)
    assert key in dto.scalars


def test_log_scalar_accepts_long_tag() -> None:
    tag = "t" * 2000
    dto = LogScalarRequestDTO(scalars={"loss": 1.0}, step=0, tags=[tag])
    assert dto.tags == [tag]
