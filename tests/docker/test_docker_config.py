from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_compose_defines_api_and_ui_services() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))

    assert set(compose["services"]) == {"api", "ui"}
    assert compose["services"]["api"]["ports"] == ["8787:8787"]
    assert compose["services"]["ui"]["ports"] == ["5173:3000"]
    assert compose["services"]["api"]["volumes"] == ["./runs:/app/runs"]
    assert compose["services"]["ui"]["depends_on"] == ["api"]


def test_dockerfiles_use_expected_runtimes() -> None:
    api_dockerfile = (ROOT / "docker" / "api.Dockerfile").read_text(encoding="utf-8")
    ui_dockerfile = (ROOT / "docker" / "ui.Dockerfile").read_text(encoding="utf-8")

    assert "ghcr.io/astral-sh/uv:" in api_dockerfile
    assert 'CMD ["persephone", "api", "--host", "0.0.0.0", "--port", "8787"]' in api_dockerfile
    assert "oven/bun:1.2.23" in ui_dockerfile
    assert "bun install --frozen-lockfile" in ui_dockerfile
    assert 'CMD ["bun", "build/index.js"]' in ui_dockerfile
