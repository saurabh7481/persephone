from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import numpy as np
from pydantic import BaseModel, Field

from persephone.core.frames import FrameIndex, FrameIndexEntry, FramePayloadRef
from persephone.storage.catalog import RunCatalog

FrameKind = Literal["field", "graph"]


class FrameListMetadata(BaseModel):
    run_id: str
    frame_count: int
    available_kinds: list[str]
    t_min: float | None = None
    t_max: float | None = None


class FrameListEntry(FrameIndexEntry):
    payload_ref: FramePayloadRef


class FrameListResponse(BaseModel):
    metadata: FrameListMetadata
    frames: list[FrameListEntry]


def list_frames(
    artifact_root: str | Path,
    run_id: str,
    *,
    kind: FrameKind | None = None,
    t_min: float | None = None,
    t_max: float | None = None,
    solver_id: str | None = None,
    max_count: int | None = None,
) -> FrameListResponse:
    run_dir = RunCatalog.scan(artifact_root).get(run_id).path
    entries = _read_index(run_dir).frames
    filtered = [
        entry
        for entry in entries
        if (kind is None or entry.kind == kind)
        and (solver_id is None or entry.solver_id == solver_id)
        and (t_min is None or entry.t >= t_min)
        and (t_max is None or entry.t <= t_max)
    ]
    available_kinds = [str(kind) for kind in sorted({entry.kind for entry in filtered})]
    times = [entry.t for entry in filtered]
    limited = filtered[:max_count] if max_count is not None else filtered

    return FrameListResponse(
        metadata=FrameListMetadata(
            run_id=run_id,
            frame_count=len(filtered),
            available_kinds=available_kinds,
            t_min=min(times) if times else None,
            t_max=max(times) if times else None,
        ),
        frames=[
            FrameListEntry(
                frame_id=entry.frame_id,
                kind=entry.kind,
                t=entry.t,
                tick=entry.tick,
                solver_id=entry.solver_id,
                source=entry.source,
                payload_ref=entry.payload_ref
                or FramePayloadRef(uri="frames/frames.jsonl", format="jsonl"),
            )
            for entry in limited
        ],
    )


def get_frame(artifact_root: str | Path, run_id: str, frame_id: str) -> dict[str, Any]:
    run_dir = RunCatalog.scan(artifact_root).get(run_id).path
    _read_index(run_dir)
    for frame in _read_jsonl(run_dir / "frames" / "frames.jsonl"):
        if frame.get("frame_id") != frame_id:
            continue
        return _hydrate_frame_payload(run_dir, frame)
    raise FrameNotFoundError(f"Frame not found: {frame_id}")


def export_frame(
    artifact_root: str | Path,
    run_id: str,
    frame_id: str,
    *,
    output: str | Path,
    export_format: Annotated[Literal["json", "csv", "npy"], Field()] = "json",
) -> Path:
    frame = get_frame(artifact_root, run_id, frame_id)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "json":
        path.write_text(json.dumps(frame, indent=2, sort_keys=True), encoding="utf-8")
        return path
    if frame.get("kind") != "field":
        raise UnsupportedFrameFormatError("CSV and NPY export currently require a field frame")
    values = frame.get("values")
    shape = frame.get("shape")
    if not isinstance(values, list) or not isinstance(shape, list):
        raise UnsupportedFrameFormatError("Field frame does not contain inline values")
    array = np.asarray(values, dtype=cast(str, frame.get("dtype", "float64"))).reshape(
        tuple(cast(list[int], shape))
    )
    if export_format == "csv":
        np.savetxt(path, array, delimiter=",")
        return path
    np.save(path, array)
    return path


def _read_index(run_dir: Path) -> FrameIndex:
    index_path = run_dir / "frames" / "index.json"
    if not index_path.exists():
        return FrameIndex(run_id=run_dir.name, frames=[])
    return FrameIndex.model_validate(json.loads(index_path.read_text(encoding="utf-8")))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _hydrate_frame_payload(run_dir: Path, frame: dict[str, Any]) -> dict[str, Any]:
    payload_ref = frame.get("payload_ref")
    if frame.get("kind") != "field" or frame.get("values") is not None:
        return frame
    if not isinstance(payload_ref, dict) or payload_ref.get("format") != "npz":
        return frame
    uri = payload_ref.get("uri")
    if not isinstance(uri, str):
        return frame
    with np.load(run_dir / uri) as loaded:
        frame["values"] = loaded["values"].reshape(-1).tolist()
    return frame


class FrameNotFoundError(ValueError):
    """Raised when a run exists but the requested frame id does not."""


class UnsupportedFrameFormatError(ValueError):
    """Raised when a frame cannot be exported in the requested representation."""


__all__ = [
    "FrameListEntry",
    "FrameListMetadata",
    "FrameListResponse",
    "FrameNotFoundError",
    "UnsupportedFrameFormatError",
    "export_frame",
    "get_frame",
    "list_frames",
]
