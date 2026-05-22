from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from persephone.core.explanations import ExplanationPacket, validate_explanation_packet


class JsonlExplanationSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write(self, packets: list[dict[str, Any]]) -> list[ExplanationPacket]:
        validated = [validate_explanation_packet(packet) for packet in packets]
        ordered = sorted(
            validated,
            key=lambda packet: (
                packet.tick,
                packet.scope,
                packet.frame_id or "",
                packet.selection_id or "",
                packet.solver_id,
            ),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for packet in ordered:
                handle.write(json.dumps(packet.model_dump(mode="json"), sort_keys=True))
                handle.write("\n")
        return ordered


__all__ = ["JsonlExplanationSink"]
