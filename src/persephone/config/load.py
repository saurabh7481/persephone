from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from persephone.config.models import ExperimentConfig

LOCAL_PATH_PARAM_KEYS = frozenset(
    {
        "contact_graph",
        "data_file",
        "data_path",
        "edge_list",
        "file",
        "fuel_map",
        "path",
    }
)
POSITIVE_PARAM_KEYS = frozenset({"dt", "ensemble_size", "n_nodes", "t_end"})


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    """Load and validate an experiment YAML file."""
    config_path = Path(path).expanduser().resolve()
    raw = _load_yaml_mapping(config_path)

    try:
        config = ExperimentConfig.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    _validate_and_resolve_params(config, config_path.parent)
    return config


def _load_yaml_mapping(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, Mapping):
        raise ValueError(f"Experiment config must be a YAML mapping: {path}")
    return raw


def _validate_and_resolve_params(config: ExperimentConfig, base_dir: Path) -> None:
    for solver in config.solvers:
        resolved_params: dict[str, Any] = {}
        for key, value in solver.params.items():
            _validate_probability_param(key, value)
            _validate_positive_param(key, value)
            resolved_params[key] = _resolve_local_path_param(key, value, base_dir)
        solver.params = resolved_params


def _validate_probability_param(key: str, value: Any) -> None:
    if not isinstance(value, int | float):
        return
    if not (key.startswith("p_") or "probability" in key or key.endswith("_prob")):
        return
    if not 0 <= float(value) <= 1:
        raise ValueError(f"Probability parameter '{key}' must be between 0 and 1")


def _validate_positive_param(key: str, value: Any) -> None:
    if key not in POSITIVE_PARAM_KEYS or not isinstance(value, int | float):
        return
    if float(value) <= 0:
        raise ValueError(f"Numeric parameter '{key}' must be positive")


def _resolve_local_path_param(key: str, value: Any, base_dir: Path) -> Any:
    if key not in LOCAL_PATH_PARAM_KEYS or not isinstance(value, str):
        return value
    if _looks_like_url(value):
        return value

    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    candidate = candidate.resolve()

    if not candidate.exists():
        raise ValueError(f"Local data source for '{key}' does not exist: {value}")
    return str(candidate)


def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://", "s3://", "gs://"))
