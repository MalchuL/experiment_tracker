"""Tests for stable and normalized MLTools model-artifact object keys."""

from mltools.clients.object_storage.client import metric_slug, model_artifact_key


def test_model_artifact_key_is_normalized() -> None:
    assert metric_slug("Validation Loss", "fold/1") == "validation-loss-fold-1"
    assert model_artifact_key("p", "j", "Validation Loss", None) == (
        "projects/p/hparam-importance/jobs/j/models/validation-loss/model.joblib"
    )
