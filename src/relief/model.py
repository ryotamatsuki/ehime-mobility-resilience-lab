"""Relief route accessibility with explicit facility data requirements."""

from __future__ import annotations

from dataclasses import dataclass


class ReliefDataUnavailable(RuntimeError):
    """Raised when official facility locations are missing."""


@dataclass(frozen=True)
class ReliefNode:
    node_id: str
    node_type: str
    name: str
    classification: str = "B"


def relief_accessibility(
    origin_to_shelter_minutes: dict[tuple[str, str], float],
    hubs: list[ReliefNode],
    shelters: list[ReliefNode],
    max_minutes: float = 180.0,
) -> dict[str, object]:
    if not hubs or not shelters:
        raise ReliefDataUnavailable("licensed relief hubs and shelters are required")
    records = []
    for hub in hubs:
        for shelter in shelters:
            minutes = origin_to_shelter_minutes.get((hub.node_id, shelter.node_id))
            if minutes is None:
                status = "unreachable_under_network"
            else:
                status = "reachable_under_network" if minutes <= max_minutes else "over_threshold"
            records.append(
                {
                    "hub_id": hub.node_id,
                    "shelter_id": shelter.node_id,
                    "travel_time_minutes": minutes,
                    "status": status,
                    "classification": "C",
                }
            )
    return {
        "metric": "relief_route_accessibility",
        "records": records,
        "limitations": ["No inventory quantity or completion guarantee is inferred."],
    }
