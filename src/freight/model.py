"""Freight model boundary; never invents inventory or enterprise supply chains."""

from __future__ import annotations

from dataclasses import dataclass


class FreightDataUnavailable(RuntimeError):
    """Raised when a requested absolute freight result lacks official inputs."""


@dataclass(frozen=True)
class FreightNode:
    node_id: str
    node_type: str
    name: str
    classification: str = "B"


def relative_freight_accessibility(
    baseline_minutes: dict[str, float],
    scenario_minutes: dict[str, float],
    nodes: list[FreightNode],
) -> dict[str, object]:
    if not nodes:
        raise FreightDataUnavailable("no licensed freight facilities are available")
    impacted = []
    for node in nodes:
        before = baseline_minutes.get(node.node_id)
        after = scenario_minutes.get(node.node_id)
        if before is None or after is None:
            continue
        impacted.append(
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "name": node.name,
                "baseline_minutes": before,
                "scenario_minutes": after,
                "delta_minutes": after - before,
                "classification": "C",
            }
        )
    return {
        "metric": "relative_freight_accessibility",
        "classification": "C",
        "nodes": impacted,
        "limitations": ["This is not an enterprise inventory or supply-chain simulation."],
    }
