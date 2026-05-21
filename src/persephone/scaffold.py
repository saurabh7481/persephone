from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScaffoldResult:
    plugin_root: Path
    package_name: str
    entry_point: str


def scaffold_plugin(name: str, output_dir: str | Path) -> ScaffoldResult:
    entry_point = _normalize_entry_point(name)
    package_name = f"persephone_{entry_point}"
    plugin_root = Path(output_dir) / f"persephone-plugin-{entry_point.replace('_', '-')}"
    package_root = plugin_root / "src" / package_name
    tests_root = plugin_root / "tests"
    package_root.mkdir(parents=True, exist_ok=False)
    tests_root.mkdir(parents=True, exist_ok=True)

    class_prefix = "".join(part.title() for part in entry_point.split("_"))
    _write(plugin_root / "pyproject.toml", _pyproject(entry_point, package_name, class_prefix))
    _write(package_root / "__init__.py", _init_py(entry_point, class_prefix))
    _write(package_root / "world.py", _world_py(class_prefix))
    _write(package_root / "solver.py", _solver_py(class_prefix, entry_point))
    _write(package_root / "observer.py", _observer_py(class_prefix, entry_point))
    _write(package_root / "renderer.py", _renderer_py(class_prefix))
    _write(plugin_root / "README.md", _readme(entry_point))
    _write(tests_root / f"test_{entry_point}_plugin.py", _test_py(package_name, class_prefix))
    return ScaffoldResult(
        plugin_root=plugin_root, package_name=package_name, entry_point=entry_point
    )


def _normalize_entry_point(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    if not normalized:
        raise ValueError("Plugin name must contain at least one alphanumeric character")
    return normalized


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _pyproject(entry_point: str, package_name: str, class_prefix: str) -> str:
    project_name = f"persephone-plugin-{entry_point.replace('_', '-')}"
    return f"""[project]
name = "{project_name}"
version = "0.1.0"
description = "Persephone simulation plugin."
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
    "persephone-sdk",
]

[project.entry-points."persephone.plugins"]
{entry_point} = "{package_name}:{class_prefix}Plugin"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{package_name}"]
"""


def _init_py(entry_point: str, class_prefix: str) -> str:
    return f'''from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import PluginManifest

from .observer import {class_prefix}Observer
from .renderer import {class_prefix}Renderer
from .solver import {class_prefix}Solver
from .world import {class_prefix}World


class {class_prefix}Plugin:
    @staticmethod
    def manifest() -> PluginManifest:
        return PluginManifest(
            name="{entry_point}",
            version="0.1.0",
            paradigm="ode",
            world={class_prefix}World,
            solver={class_prefix}Solver,
            observer={class_prefix}Observer,
            renderer={class_prefix}Renderer,
            bus_reads=[],
            bus_writes=["value"],
            default_params=default_params(),
            params_schema=dict(
                type="object",
                properties=dict(initial_value=dict(type="number")),
            ),
            metrics_schema=dict(value=dict(type="number")),
            sdk_min_version="0.1.0",
        )


def default_params() -> dict[str, Any]:
    return dict(initial_value=1.0)
'''


def _world_py(class_prefix: str) -> str:
    return """from __future__ import annotations

from typing import Any

import numpy as np
from persephone_sdk.plugin import World
from persephone_sdk.types import StateDict


class __CLASS__World(World):
    def __init__(self) -> None:
        self._initial: StateDict | None = None

    def schema(self) -> dict[str, tuple[int, ...]]:
        return {"value": (1,)}

    def init(self, params: dict[str, Any], seed: int) -> StateDict:
        state = {"value": np.array([float(params.get("initial_value", 1.0))])}
        self._initial = {"value": state["value"].copy()}
        return state

    def reset(self) -> StateDict:
        if self._initial is None:
            return self.init({}, seed=0)
        return {"value": self._initial["value"].copy()}
""".replace("__CLASS__", class_prefix)


def _solver_py(class_prefix: str, entry_point: str) -> str:
    return """from __future__ import annotations

from persephone_sdk.plugin import Solver
from persephone_sdk.types import StateDict


class __CLASS__Solver(Solver):
    @property
    def preferred_dt(self) -> float:
        return 1.0

    def step(self, state: StateDict, dt: float, bus: object) -> tuple[StateDict, float]:
        next_state = {"value": state["value"] + dt}
        if hasattr(bus, "write"):
            bus.write("value", next_state["value"], solver_id="__ENTRY__", tick=0)
        return next_state, dt
""".replace("__CLASS__", class_prefix).replace("__ENTRY__", entry_point)


def _observer_py(class_prefix: str, entry_point: str) -> str:
    return """from __future__ import annotations

from persephone_sdk.plugin import Observer
from persephone_sdk.types import MetricRecord, StateDict


class __CLASS__Observer(Observer):
    def observe(self, state: StateDict, t: float, run_id: str) -> list[MetricRecord]:
        return [
            {
                "run_id": run_id,
                "solver_id": "__ENTRY__",
                "metric": "value",
                "value": float(state["value"][0]),
                "t": t,
                "tags": {},
            }
        ]
""".replace("__CLASS__", class_prefix).replace("__ENTRY__", entry_point)


def _renderer_py(class_prefix: str) -> str:
    return """from __future__ import annotations

from typing import Any

from persephone_sdk.plugin import Renderer


class __CLASS__Renderer(Renderer):
    def viz_schema(self) -> dict[str, Any]:
        return {"metrics": ["value"]}
""".replace("__CLASS__", class_prefix)


def _test_py(package_name: str, class_prefix: str) -> str:
    return f"""from __future__ import annotations

from persephone_sdk.testing import PluginTestHarness
from {package_name} import {class_prefix}Plugin


def test_plugin_passes_sdk_harness() -> None:
    PluginTestHarness({class_prefix}Plugin).run_all()
"""


def _readme(entry_point: str) -> str:
    return f"""# persephone-plugin-{entry_point.replace("_", "-")}

Generated Persephone plugin scaffold.

Run the harness with:

```bash
uv run pytest
```
"""
