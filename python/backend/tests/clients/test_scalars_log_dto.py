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


@pytest.mark.parametrize(
    ("wire_value", "metric_name"),
    [
        ("nan", "nan_metric"),
        ("inf", "inf_metric"),
        ("-inf", "neg_inf_metric"),
    ],
)
def test_log_scalar_accepts_non_finite_wire_values(
    wire_value: str, metric_name: str
) -> None:
    dto = LogScalarRequestDTO(scalars={metric_name: wire_value}, step=3, tags=None)
    assert dto.scalars[metric_name] == wire_value


def test_scalar_series_accepts_non_finite_wire_y_values() -> None:
    from clients.scalars.dto import ScalarSeriesDTO

    series = ScalarSeriesDTO(x=[1, 2, 3], y=[0.5, "nan", "inf"])
    assert series.y == [0.5, "nan", "inf"]
