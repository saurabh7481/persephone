from __future__ import annotations

from typing import Any

from persephone.config.models import ExperimentConfig


def experiment_config_json_schema() -> dict[str, Any]:
    """Return the JSON Schema for Persephone experiment configs."""
    return ExperimentConfig.model_json_schema()
