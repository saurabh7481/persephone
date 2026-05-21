from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContactGraph:
    n_nodes: int
    adjacency: tuple[tuple[tuple[int, float], ...], ...]

    @classmethod
    def from_csv(cls, path: str | Path, n_nodes: int | None = None) -> ContactGraph:
        edge_rows: list[tuple[int, int, float]] = []
        max_node = -1
        with Path(path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"source", "target", "weight"}
            if set(reader.fieldnames or []) < required:
                raise ValueError("Contact graph CSV must include source,target,weight columns")
            for row in reader:
                source = int(row["source"])
                target = int(row["target"])
                weight = float(row["weight"])
                if source < 0 or target < 0:
                    raise ValueError("Node ids must be non-negative")
                if weight < 0:
                    raise ValueError("Edge weights must be non-negative")
                edge_rows.append((source, target, weight))
                max_node = max(max_node, source, target)

        inferred_nodes = max_node + 1
        node_count = inferred_nodes if n_nodes is None else n_nodes
        if node_count < inferred_nodes:
            raise ValueError(f"n_nodes={node_count} cannot contain node id {max_node}")

        adjacency: list[list[tuple[int, float]]] = [[] for _ in range(node_count)]
        for source, target, weight in edge_rows:
            adjacency[source].append((target, weight))
            adjacency[target].append((source, weight))

        return cls(
            n_nodes=node_count,
            adjacency=tuple(tuple(neighbors) for neighbors in adjacency),
        )

    def neighbors(self, node_id: int) -> list[tuple[int, float]]:
        return list(self.adjacency[node_id])
