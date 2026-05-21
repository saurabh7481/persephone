from __future__ import annotations

from fastapi.testclient import TestClient

from persephone.api.app import create_app


def test_api_lists_and_fetches_example_configs() -> None:
    client = TestClient(create_app())

    listed = client.get("/examples")
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert {"sir_epidemic", "heat_diffusion"} <= ids

    fetched = client.get("/examples/heat_diffusion")
    assert fetched.status_code == 200
    assert fetched.json()["config"]["solvers"][0]["plugin"] == "heat_diffusion"


def test_deprecated_sir_example_alias_still_returns_config() -> None:
    client = TestClient(create_app())

    response = client.get("/examples/sir_epidemic")

    assert response.status_code == 200
    assert response.json()["solvers"][0]["plugin"] == "sir_epidemic"
