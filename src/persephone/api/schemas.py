from __future__ import annotations

from pydantic import BaseModel

from persephone.config.models import ExperimentConfig


class RunCreateRequest(BaseModel):
    config: ExperimentConfig
    run_id: str | None = None
