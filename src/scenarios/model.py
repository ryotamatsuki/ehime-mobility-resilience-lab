"""Serializable stress-test scenarios and result-state labels."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Scenario:
    scenario_id: str
    title: str
    description: str
    network_version: str
    gtfs_version: str | None
    od_model_version: str
    disabled_links: list[str] = field(default_factory=list)
    capacity_reductions: dict[str, float] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    result_version: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    classification: str = "D"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Scenario":
        return cls(**{key: value[key] for key in cls.__dataclass_fields__ if key in value})


@dataclass
class ScenarioResult:
    scenario_id: str
    state: str
    metrics: dict[str, Any]
    provenance: dict[str, Any]

    @property
    def is_computed(self) -> bool:
        return self.state == "computed"
