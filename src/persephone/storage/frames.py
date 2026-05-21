from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np

from persephone.core.frames import (
    FieldFrame,
    FrameIndex,
    FrameIndexEntry,
    FramePayloadRef,
    validate_frame,
)


class FrameSink(Protocol):
    def write(
        self,
        frames: list[dict[str, Any]],
        *,
        inline_frame_max_values: int,
    ) -> list[FrameIndexEntry]:
        """Persist frames and return index entries for replay discovery."""


class JsonlFrameSink:
    def __init__(self, run_dir: str | Path, run_id: str) -> None:
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.frame_dir = self.run_dir / "frames"
        self.payload_dir = self.frame_dir / "payloads"

    def write(
        self,
        frames: list[dict[str, Any]],
        *,
        inline_frame_max_values: int,
    ) -> list[FrameIndexEntry]:
        if not frames:
            return []

        self.frame_dir.mkdir(parents=True, exist_ok=True)
        persisted: list[dict[str, Any]] = []
        entries: list[FrameIndexEntry] = []
        jsonl_ref = FramePayloadRef(uri="frames/frames.jsonl", format="jsonl")

        for raw_frame in frames:
            frame = validate_frame(raw_frame)
            payload = frame.model_dump(mode="json")
            payload_ref = jsonl_ref
            if isinstance(frame, FieldFrame) and frame.values is not None:
                if len(frame.values) > inline_frame_max_values:
                    payload_ref = self._write_npz_payload(frame)
                    payload["payload_ref"] = payload_ref.model_dump(mode="json")
                    payload["values"] = None
                else:
                    payload["payload_ref"] = jsonl_ref.model_dump(mode="json")
            persisted.append(payload)
            entries.append(
                FrameIndexEntry(
                    frame_id=frame.frame_id,
                    kind=cast(Any, frame.kind),
                    t=frame.t,
                    tick=frame.tick,
                    solver_id=frame.solver_id,
                    source=frame.source,
                    payload_ref=payload_ref,
                )
            )

        _append_jsonl(self.frame_dir / "frames.jsonl", persisted)
        self._append_index(entries)
        return entries

    def _write_npz_payload(self, frame: FieldFrame) -> FramePayloadRef:
        self.payload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{_safe_frame_id(frame.frame_id)}.npz"
        uri = f"frames/payloads/{filename}"
        path = self.run_dir / uri
        array = np.asarray(frame.values, dtype=frame.dtype).reshape(frame.shape)
        np.savez_compressed(path, values=array)
        return FramePayloadRef(uri=uri, format="npz")

    def _append_index(self, entries: list[FrameIndexEntry]) -> None:
        path = self.frame_dir / "index.json"
        existing: list[FrameIndexEntry] = []
        if path.exists():
            current = FrameIndex.model_validate(json.loads(path.read_text(encoding="utf-8")))
            existing = current.frames
        index = FrameIndex(run_id=self.run_id, frames=[*existing, *entries])
        _write_json_atomic(path, index.model_dump(mode="json"))


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def _safe_frame_id(frame_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", frame_id).strip("_") or "frame"


__all__ = ["FrameSink", "JsonlFrameSink"]
