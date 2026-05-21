from __future__ import annotations

from pathlib import Path

import numpy as np

from persephone.config.load import load_experiment_config
from persephone.core.engine import PersephoneEngine
from persephone.fields import export_field_artifact, list_field_artifacts


def test_field_artifacts_list_final_and_checkpoint_2d_arrays(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/heat_diffusion.yaml")
    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(config, run_id="field-run")
    assert result.status == "completed"

    fields = list_field_artifacts(tmp_path / "runs", "field-run")

    temperature_fields = [field for field in fields if field.name.endswith(".temperature")]
    assert {field.source for field in temperature_fields} >= {"final_state", "checkpoint"}
    assert temperature_fields[0].dimensions == [12, 12]
    assert temperature_fields[0].dtype.startswith("float")
    assert temperature_fields[0].units == "temperature"
    assert temperature_fields[0].visualization["kind"] == "heatmap"


def test_field_artifact_export_writes_csv(tmp_path: Path) -> None:
    config = load_experiment_config("configs/examples/heat_diffusion.yaml")
    result = PersephoneEngine(artifact_root=tmp_path / "runs").run(config, run_id="field-export")
    assert result.status == "completed"

    artifact = next(
        field
        for field in list_field_artifacts(tmp_path / "runs", "field-export")
        if field.source == "final_state" and field.name.endswith(".temperature")
    )
    output = export_field_artifact(
        tmp_path / "runs",
        "field-export",
        artifact.id,
        output=tmp_path / "temperature.csv",
        export_format="csv",
    )

    exported = np.loadtxt(output, delimiter=",")
    assert exported.shape == (12, 12)
