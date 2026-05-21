from __future__ import annotations

from fastapi.testclient import TestClient

from persephone.api.app import create_app


def test_api_lists_and_fetches_example_configs() -> None:
    client = TestClient(create_app())

    listed = client.get("/examples")
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert {"sir_epidemic", "heat_diffusion", "heat_diffusion_large", "us_county_epidemic"} <= ids

    fetched = client.get("/examples/heat_diffusion")
    assert fetched.status_code == 200
    assert fetched.json()["config"]["solvers"][0]["plugin"] == "heat_diffusion"

    large = client.get("/examples/heat_diffusion_large")
    assert large.status_code == 200
    large_config = large.json()["config"]
    assert large_config["solvers"][0]["params"]["width"] == 96
    assert large_config["visualization"]["emit_every"] == 0.25
    assert large_config["scheduler"]["demo_delay_ms_per_tick"] == 25

    county = client.get("/examples/us_county_epidemic")
    assert county.status_code == 200
    assert county.json()["config"]["solvers"][0]["plugin"] == "us_county_epidemic"


def test_deprecated_sir_example_alias_still_returns_config() -> None:
    client = TestClient(create_app())

    response = client.get("/examples/sir_epidemic")

    assert response.status_code == 200
    assert response.json()["solvers"][0]["plugin"] == "sir_epidemic"
