from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import APIRouter

from persephone.api.schemas import ExampleConfigResponse, ExampleSummaryResponse
from persephone.config.load import load_experiment_config

router = APIRouter()


@dataclass(frozen=True)
class ExampleConfig:
    id: str
    name: str
    description: str
    path: str


EXAMPLES = {
    "sir_epidemic": ExampleConfig(
        id="sir_epidemic",
        name="SIR epidemic baseline",
        description="Synthetic graph simulation with population state metrics.",
        path="configs/examples/sir_epidemic.yaml",
    ),
    "heat_diffusion": ExampleConfig(
        id="heat_diffusion",
        name="Heat diffusion baseline",
        description="2D field simulation with scalar field metrics.",
        path="configs/examples/heat_diffusion.yaml",
    ),
    "heat_diffusion_large": ExampleConfig(
        id="heat_diffusion_large",
        name="Heat diffusion large demo",
        description="Larger heat field with dense playback frames and a paced demo runtime.",
        path="configs/examples/heat_diffusion_large.yaml",
    ),
    "us_county_epidemic": ExampleConfig(
        id="us_county_epidemic",
        name="U.S. county epidemic demo",
        description="Real-world county adjacency simulation backed by the 2023 U.S. Census file.",
        path="configs/examples/us_county_epidemic.yaml",
    ),
}


@router.get("/examples", response_model=list[ExampleSummaryResponse])
def list_examples() -> list[dict[str, object]]:
    return [
        {"id": example.id, "name": example.name, "description": example.description}
        for example in EXAMPLES.values()
    ]


@router.get("/examples/sir_epidemic", response_model=dict[str, object])
def sir_epidemic_example() -> dict[str, object]:
    return cast(dict[str, object], example_config("sir_epidemic")["config"])


@router.get("/examples/{example_id}", response_model=ExampleConfigResponse)
def example_config(example_id: str) -> dict[str, object]:
    example = EXAMPLES[example_id]
    config = load_experiment_config(example.path)
    return {
        "id": example.id,
        "name": example.name,
        "description": example.description,
        "config": config.model_dump(mode="json"),
    }
