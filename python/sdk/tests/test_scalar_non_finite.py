import math

from experiment_tracker_sdk.client.domain.scalars.dto import LogScalarRequest, LogScalarsRequest
from experiment_tracker_sdk.client.transport.errors import convert_payload_to_json


def test_log_scalar_request_serializes_non_finite_to_wire() -> None:
    request = LogScalarRequest(
        scalars={
            "finite": 1.5,
            "nan_metric": math.nan,
            "inf_metric": math.inf,
            "neg_inf_metric": -math.inf,  # metric name; wire value is "-inf"
        },
        step=7,
    )
    payload = convert_payload_to_json(request)
    assert payload is not None
    assert payload["scalars"] == {
        "finite": 1.5,
        "nan_metric": "nan",
        "inf_metric": "inf",
        "neg_inf_metric": "-inf",
    }
    assert payload["step"] == 7


def test_log_scalars_batch_serializes_non_finite_to_wire() -> None:
    batch = LogScalarsRequest(
        scalars=[
            LogScalarRequest(scalars={"loss": math.nan}, step=1),
            LogScalarRequest(scalars={"loss": math.inf}, step=2),
        ]
    )
    payload = convert_payload_to_json(batch)
    assert payload is not None
    assert payload["scalars"][0]["scalars"] == {"loss": "nan"}
    assert payload["scalars"][1]["scalars"] == {"loss": "inf"}
