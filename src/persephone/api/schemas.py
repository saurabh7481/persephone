from __future__ import annotations

from pydantic import BaseModel

from persephone.config.models import ExperimentConfig
from persephone.sweeps import ScalarValue, SweepConfig


class RunCreateRequest(BaseModel):
    config: ExperimentConfig
    run_id: str | None = None


class SweepCreateRequest(BaseModel):
    name: str
    base_config: ExperimentConfig
    parameter: str
    values: list[ScalarValue]
    sweep_id: str | None = None

    def to_sweep_config(self) -> SweepConfig:
        return SweepConfig(
            sweep_id=self.sweep_id,
            name=self.name,
            base_config=self.base_config,
            parameter=self.parameter,
            values=self.values,
        )
