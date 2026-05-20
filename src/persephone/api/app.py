from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from persephone.api.manager import RunManager
from persephone.api.routes import compare as compare_routes
from persephone.api.routes import examples as examples_routes
from persephone.api.routes import health as health_routes
from persephone.api.routes import plugins as plugins_routes
from persephone.api.routes import runs as runs_routes
from persephone.api.routes import sweeps as sweeps_routes


def create_app(artifact_root: str | Path = "runs") -> FastAPI:
    app = FastAPI(
        title="Persephone Local API",
        version="0.1.0",
        description="Local-only control API for running and inspecting Persephone simulations.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.run_manager = RunManager(artifact_root=artifact_root)
    app.state.artifact_root = Path(artifact_root)
    app.include_router(health_routes.router)
    app.include_router(examples_routes.router)
    app.include_router(plugins_routes.router)
    app.include_router(runs_routes.router)
    app.include_router(sweeps_routes.router)
    app.include_router(compare_routes.router)

    return app
