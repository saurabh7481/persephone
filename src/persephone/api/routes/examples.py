from __future__ import annotations

from fastapi import APIRouter

from persephone.config.load import load_experiment_config

router = APIRouter()


@router.get("/examples/sir_epidemic")
def sir_epidemic_example() -> dict[str, object]:
    config = load_experiment_config("configs/examples/sir_epidemic.yaml")
    return config.model_dump(mode="json")
