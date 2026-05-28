from __future__ import annotations

import importlib
import importlib.util
import logging
from typing import Any

from ...console.utils.bootstrap import register_run_bootstrap_hook
from ...console.utils.context import RunCliContext

_defaults_registered = False
_active_tracker: Any | None = None
_logger = logging.getLogger(__name__)


def _global_step_or_zero(global_step: Any) -> int:
    if global_step is None:
        return 0
    try:
        return int(global_step)
    except (TypeError, ValueError):
        return 0


def _walltime_or_zero(walltime: Any) -> float:
    if walltime is None:
        return 0
    try:
        return float(walltime)
    except (TypeError, ValueError):
        return 0


def _scalar_to_float(value: Any) -> float:
    """Convert tensor/numpy scalar-like values to a plain float."""
    if hasattr(value, "detach") and callable(value.detach):
        value = value.detach()
    if hasattr(value, "cpu") and callable(value.cpu):
        value = value.cpu()
    if hasattr(value, "item") and callable(value.item):
        value = value.item()
    return float(value)


def _tensor_to_numpy_like(value: Any) -> Any:
    """Convert tensor-like inputs to numpy arrays when possible."""
    if hasattr(value, "detach") and callable(value.detach):
        value = value.detach()
    if hasattr(value, "cpu") and callable(value.cpu):
        value = value.cpu()
    if hasattr(value, "numpy") and callable(value.numpy):
        return value.numpy()
    return value


def _prepare_image_for_tracker(img_tensor: Any, dataformats: Any) -> Any:
    """Convert TensorBoard image layouts to tracker-supported image layouts."""
    image = _tensor_to_numpy_like(img_tensor)
    try:
        import numpy as np  # type: ignore[import-not-found]
    except Exception:
        return image
    if not isinstance(image, np.ndarray):
        return image

    fmt = str(dataformats or "CHW").upper()
    if fmt.startswith("N") and image.ndim >= 4:
        image = image[0]
        fmt = fmt[1:]
    if fmt == "CHW" and image.ndim == 3:
        if image.shape[0] == 1:
            return image[0]
        return np.moveaxis(image, 0, -1)
    if fmt == "HWC" and image.ndim == 3 and image.shape[2] == 1:
        return image[:, :, 0]
    return image


def _image_dataformats(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    if "dataformats" in kwargs:
        return kwargs["dataformats"]
    if args:
        return args[0]
    return "CHW"


def _feature_name(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


def _hyperparameters_to_features(hparam_dict: Any) -> list[dict[str, Any]]:
    if not isinstance(hparam_dict, dict):
        return []
    children = [
        {"name": f"{key}: {_feature_name(value)}"}
        for key, value in sorted(hparam_dict.items(), key=lambda item: str(item[0]))
    ]
    if not children:
        return []
    return [{"name": "hyperparameters", "children": children}]


def _merge_feature_branch(
    existing_features: Any,
    branch: dict[str, Any],
) -> list[Any]:
    existing = list(existing_features or [])
    merged: list[Any] = []
    replaced = False
    for feature in existing:
        name = None
        if isinstance(feature, dict):
            name = feature.get("name")
        else:
            name = getattr(feature, "name", None)
        if name == branch["name"]:
            merged.append(branch)
            replaced = True
        else:
            merged.append(feature)
    if not replaced:
        merged.append(branch)
    return merged


def _tracker_features(tracker: Any) -> Any:
    experiment = getattr(tracker, "_experiment", None)
    if experiment is None:
        return []
    return getattr(experiment, "features", [])


def _patch_summary_writer(writer_cls: type[Any]) -> None:
    """Patch one SummaryWriter class so TensorBoard calls also hit the tracker."""
    if getattr(writer_cls, "_experiment_tracker_sdk_patched", False):
        return

    original_add_scalar = getattr(writer_cls, "add_scalar", None)
    if callable(original_add_scalar):

        def add_scalar(  # type: ignore[no-untyped-def]
            self,
            tag,
            scalar_value,
            global_step=None,
            walltime=None,
            *args,
            **kwargs,
        ):
            tracker = _active_tracker
            if tracker is not None:
                try:
                    tracker.add_scalar(
                        tag,
                        _scalar_to_float(scalar_value),
                        global_step=_global_step_or_zero(global_step),
                        walltime=_walltime_or_zero(walltime),
                    )
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "tensorboard_scalar_capture_failed",
                        extra={"tag": tag, "error": str(exc)},
                    )
            return original_add_scalar(
                self,
                tag,
                scalar_value,
                global_step,
                walltime,
                *args,
                **kwargs,
            )

        writer_cls.add_scalar = add_scalar  # type: ignore[method-assign]

    original_add_image = getattr(writer_cls, "add_image", None)
    if callable(original_add_image):

        def add_image(  # type: ignore[no-untyped-def]
            self,
            tag,
            img_tensor,
            global_step=None,
            walltime=None,
            *args,
            **kwargs,
        ):
            tracker = _active_tracker
            if tracker is not None:
                try:
                    tracker_image = _prepare_image_for_tracker(
                        img_tensor,
                        _image_dataformats(args, kwargs),
                    )
                    tracker.add_image(
                        tag,
                        tracker_image,
                        global_step=_global_step_or_zero(global_step),
                        walltime=_walltime_or_zero(walltime),
                    )
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "tensorboard_image_capture_failed",
                        extra={"tag": tag, "error": str(exc)},
                    )
            return original_add_image(
                self,
                tag,
                img_tensor,
                global_step,
                walltime,
                *args,
                **kwargs,
            )

        writer_cls.add_image = add_image  # type: ignore[method-assign]

    original_add_hparams = getattr(writer_cls, "add_hparams", None)
    if callable(original_add_hparams):

        def add_hparams(self, hparam_dict, metric_dict=None, *args, **kwargs):  # type: ignore[no-untyped-def]
            tracker = _active_tracker
            if tracker is not None:
                try:
                    features = _hyperparameters_to_features(hparam_dict)
                    if features:
                        tracker.features(
                            _merge_feature_branch(
                                _tracker_features(tracker),
                                features[0],
                            )
                        )
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "tensorboard_hparams_capture_failed",
                        extra={"error": str(exc)},
                    )
            return original_add_hparams(
                self,
                hparam_dict,
                metric_dict,
                *args,
                **kwargs,
            )

        writer_cls.add_hparams = add_hparams  # type: ignore[method-assign]

    writer_cls._experiment_tracker_sdk_patched = True  # type: ignore[attr-defined]


def _patch_summary_writer_module(module_name: str) -> None:
    try:
        spec = importlib.util.find_spec(module_name)
    except ModuleNotFoundError:
        return
    if spec is None:
        return
    module = importlib.import_module(module_name)
    writer_cls = getattr(module, "SummaryWriter", None)
    if isinstance(writer_cls, type):
        _patch_summary_writer(writer_cls)


def monkey_patch_tensorboard(tracker: Any | None = None) -> None:
    """Patch installed TensorBoard writer implementations.

    Args:
        tracker: Optional tracker to receive mirrored SummaryWriter calls.
            When omitted, the currently active tracker is left unchanged.
    """
    global _active_tracker
    if tracker is not None:
        _active_tracker = tracker
    for name in ("tensorboard", "tensorboardX"):
        try:
            spec = importlib.util.find_spec(name)
        except ModuleNotFoundError:
            continue
        if spec is None:
            continue
        importlib.import_module(name)  # noqa: F401 - side effect / warm import
    for module_name in ("tensorboardX", "torch.utils.tensorboard"):
        try:
            _patch_summary_writer_module(module_name)
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "tensorboard_summary_writer_patch_failed",
                extra={"module_name": module_name, "error": str(exc)},
            )


def _tensorboard_bootstrap(ctx: RunCliContext) -> None:
    """TensorBoard / TensorBoardX setup for in-process ``run``.

    When a run tracker is initialized, patch installed SummaryWriter
    implementations so ``add_scalar`` and ``add_image`` are mirrored to the
    experiment tracker. TensorBoard dependencies stay optional.
    """
    global _active_tracker
    _active_tracker = None if ctx.runner is None else ctx.runner.exp_tracker
    monkey_patch_tensorboard()


def register_default_tensorboard_hooks() -> None:
    """Idempotently register built-in TensorBoard bootstrap behavior."""
    global _defaults_registered
    if _defaults_registered:
        return
    _defaults_registered = True
    register_run_bootstrap_hook(_tensorboard_bootstrap)
