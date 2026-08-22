"""A1.12: vulnerable-population and equity analysis for the Ozu A1 model.

A1.11 is regenerated first so all hospital, shelter, temporal and criticality
outputs remain available. A1.12 does not invent a vulnerability score. It
reweights the already-computed 08:00 accessibility results with the age fields
that already exist in the 2020 simplified 100 m population dataset:
65+, 75+ and 85+.

Ozu City's 2026-07-31 region/age population open data is used only as current
official context. It is deliberately NOT spatially downscaled to the 100 m
mesh, avoiding false precision from mixing 2026 regional totals with the 2020
mesh distribution.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from accessibility.equity import (
    AGE_GROUP_FIELDS,
    enrich_100m_age_weights,
    equity_gaps,
    group_access_metrics,
    official_region_age_context,
)
from common.provenance import make_provenance
from scripts.build_network.build_a1_1 import POP_LANDING, POP_URL, fetch, first_csv_rows
from scripts.build_network.build_a1_5 import OFFICIAL_MEDICAL_LANDING
from scripts.build_network.build_a1_9 import SHELTER_LANDING
from scripts.build_network.build_a1_11 import build as build_a1_11

AGE_POP_URL = "https://www.city.ozu.ehime.jp/uploaded/attachment/48246.zip"
AGE_POP_LANDING = "https://www.city.ozu.ehime.jp/site/opendata/41647.html"
AGE_POP_AS_OF = "2026-07-31"
GROUP_LABELS = {
    "all": "全人口",
    "65plus": "65歳以上",
    "75plus": "75歳以上",
    "85plus": "85歳以上",
}
DESTINATION_SPECS = {
    "hospital": ("病院", "baseline_minutes", "disrupted_minutes"),
    "emergency": ("指定緊急避難場所", "emergency_baseline_minutes", "emergency_disrupted_minutes"),
    "general": ("指定一般避難所", "general_baseline_minutes", "general_disrupted_minutes"),
    "welfare": ("指定福祉避難所", "welfare_baseline_minutes", "welfare_disrupted_minutes"),
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _join_access_and_age(output: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    hospital = read_json(output / "population_access.geojson")
    shelters = read_json(output / "shelter_population_access.geojson")
    if hospital.get("type") != "FeatureCollection" or shelters.get("type") != "FeatureCollection":
        raise ValueError("A1.12 predecessor population GeoJSON contract invalid")

    shelter_by_id = {
        str((feature.get("properties") or {}).get("zone_id") or feature.get("id")): feature
        for feature in shelters.get("features") or []
    }
    population_rows = first_csv_rows(fetch(POP_URL))
    age_by_mesh = enrich_100m_age_weights(population_rows)

    features: list[dict[str, Any]] = []
    missing_age = 0
    missing_shelter = 0
    for source_feature in hospital.get("features") or []:
        props = dict(source_feature.get("properties") or {})
        zone_id = str(props.get("zone_id") or source_feature.get("id") or "")
        age = age_by_mesh.get(zone_id)
        if age is None:
            missing_age += 1
            continue
        shelter_feature = shelter_by_id.get(zone_id)
        if shelter_feature is None:
            missing_shelter += 1
            continue
        shelter_props = shelter_feature.get("properties") or {}
        props.update(age)
        for key, value in shelter_props.items():
            if key.endswith("_baseline_minutes") or key.endswith("_disrupted_minutes") or key.endswith("_delta_minutes"):
                props[key] = value
        props["age_population_source_classification"] = "B"
        props["accessibility_classification"] = "C"
        features.append({
            "type": "Feature",
            "id": zone_id,
            "properties": props,
            "geometry": source_feature.get("geometry"),
        })

    if not features or missing_age or missing_shelter:
        raise ValueError(
            f"A1.12 population join incomplete: features={len(features)}, missing_age={missing_age}, missing_shelter={missing_shelter}"
        )

    totals = {
        group: round(sum(float((f["properties"] or {}).get(field) or 0.0) for f in features), 4)
        for group, field in AGE_GROUP_FIELDS.items()
    }
    if not (0 <= totals["85plus"] <= totals["75plus"] <= totals["65plus"] <= totals["all"]):
        raise ValueError("A1.12 age population monotonicity failed")
    return features, {"source_rows": len(population_rows), "group_totals": totals}


def _destination_equity(features: list[dict[str, Any]]) -> dict[str, Any]:
    destinations: dict[str, Any] = {}
    for destination, (label, baseline_key, disrupted_key) in DESTINATION_SPECS.items():
        groups: dict[str, Any] = {}
        for group, weight_key in AGE_GROUP_FIELDS.items():
            groups[group] = group_access_metrics(
                features,
                weight_key=weight_key,
                baseline_key=baseline_key,
                disrupted_key=disrupted_key,
            )
        destinations[destination] = {
            "label": label,
            "baseline_key": baseline_key,
            "disrupted_key": disrupted_key,
            "groups": groups,
            "gaps_vs_all": equity_gaps(groups),
        }
    return destinations


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    predecessor = build_a1_11(output)

    features, population_meta = _join_access_and_age(output)
    destinations = _destination_equity(features)
    official_context = official_region_age_context(fetch(AGE_POP_URL))

    mesh_totals = population_meta["group_totals"]
    mesh_context = {
        "population": mesh_totals["all"],
        "population_65plus": mesh_totals["65plus"],
        "population_75plus": mesh_totals["75plus"],
        "population_85plus": mesh_totals["85plus"],
        "share_65plus_pct": None if mesh_totals["all"] <= 0 else round(100 * mesh_totals["65plus"] / mesh_totals["all"], 3),
        "share_75plus_pct": None if mesh_totals["all"] <= 0 else round(100 * mesh_totals["75plus"] / mesh_totals["all"], 3),
        "share_85plus_pct": None if mesh_totals["all"] <= 0 else round(100 * mesh_totals["85plus"] / mesh_totals["all"], 3),
    }

    equity_summary = {
        "stage": "A1.12",
        "status": "computed",
        "analysis_time": "08:00",
        "scenario": predecessor.get("scenario", {}).get("id"),
        "groups": [
            {"id": group, "label": GROUP_LABELS[group], "weight_field": AGE_GROUP_FIELDS[group]}
            for group in AGE_GROUP_FIELDS
        ],
        "destinations": destinations,
        "population_sources": {
            "mesh_age_population": {
                "source": POP_LANDING,
                "reference_year": 2020,
                "classification": "B",
                "method": "source-provided simplified 100 m age-group estimates; no A1.12 downscaling",
                "fields": ["PopT", "Pop65over", "Pop75over", "Pop85over"],
                "analysis_envelope": mesh_context,
            },
            "current_official_context": {
                "source": AGE_POP_LANDING,
                "as_of": AGE_POP_AS_OF,
                "classification": "A",
                "license": "CC BY 4.0",
                "usage": "citywide/current context only; not used to overwrite or downscale the 2020 100 m grid",
                "raw_archive_published": False,
                **official_context,
            },
        },
        "interpretation": {
            "equity_gap": "age-group burden minus all-population burden; affected-share gap is percentage points",
            "composite_score": False,
            "vulnerable_population_claim": "age groups are shown separately; A1.12 does not claim they equal all people requiring special assistance",
        },
    }

    provenance = make_provenance(
        "a1-12-ozu-vulnerable-population-equity",
        "C",
        "minimal-multimodal-v0.1.12",
        [
            {"dataset_id": "ozu_population_100m_2020_age", "source": POP_LANDING, "classification": "B", "license": "CC BY", "usage": "direct 100 m Pop65over/Pop75over/Pop85over weights"},
            {"dataset_id": "ozu_region_age_population_20260731", "source": AGE_POP_LANDING, "classification": "A", "license": "CC BY 4.0", "usage": "current citywide context only; no spatial downscaling"},
            {"dataset_id": "ehime_medical_registry_verification", "source": OFFICIAL_MEDICAL_LANDING, "classification": "A", "usage": "predecessor hospital verification"},
            {"dataset_id": "ozu_shelter_registry", "source": SHELTER_LANDING, "classification": "A", "license": "CC BY 4.0", "usage": "predecessor shelter destinations"},
        ],
        {
            "analysis_time": "08:00:00",
            "groups": list(AGE_GROUP_FIELDS),
            "destinations": list(DESTINATION_SPECS),
            "equity_metrics": ["affected_share_gt1min_pct", "mean_minutes_change", "gap_vs_all"],
            "composite_score": False,
            "spatial_downscaling_from_2026_official_region_data": False,
        },
        scenario_id="ozu-clockwise-loop-unavailable-equity",
        limitations=[
            "The 100 m age-group weights are 2020 simplified census-derived estimates (B), not 2026 observed residential locations.",
            "The 2026-07-31 Ozu region/age table is current official context (A) but is not downscaled to the 100 m grid because that would create false spatial precision.",
            "Age 65+/75+/85+ are reported separately and do not represent the full population requiring special assistance.",
            "Equity gaps are descriptive accessibility differences, not causal estimates or normative priority scores.",
            "Accessibility remains a C model estimate and the route outage remains a D stress-test assumption.",
            "Shelter accessibility uses the verified subset of official shelters in the current GTFS analysis envelope.",
        ],
        repository=ROOT,
    )

    summary = dict(predecessor)
    summary.update({
        "stage": "A1.12",
        "title": "大洲市 Vulnerable Population / Equity Analysis",
        "provenance": provenance,
        "vulnerable_population": {
            "groups": list(AGE_GROUP_FIELDS),
            "mesh_source_classification": "B",
            "mesh_reference_year": 2020,
            "current_official_context_as_of": AGE_POP_AS_OF,
            "current_official_context_classification": "A",
            "spatial_downscaling_performed": False,
            "group_totals_in_analysis_envelope": mesh_totals,
        },
        "equity_analysis": {
            "analysis_time": "08:00",
            "destinations": list(DESTINATION_SPECS),
            "composite_score": False,
            "hospital": destinations["hospital"],
            "welfare": destinations["welfare"],
        },
    })

    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "equity_summary.json").write_text(json.dumps(equity_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "vulnerable_population_access.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps({
        "stage": "A1.12",
        "mesh_group_totals": mesh_totals,
        "current_official_context": official_context,
        "hospital_gaps": destinations["hospital"]["gaps_vs_all"],
        "welfare_gaps": destinations["welfare"]["gaps_vs_all"],
    }, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_12")
    args = parser.parse_args()
    summary = build(args.output)
    return 0 if summary.get("stage") == "A1.12" else 2


if __name__ == "__main__":
    raise SystemExit(main())
