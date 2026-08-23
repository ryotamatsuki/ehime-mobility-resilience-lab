"""Transparent population-group weighting for A1.12 equity analysis.

No composite vulnerability score is calculated here. Each age group remains an
independent population weight, and equity gaps are reported as simple
percentage-point or minute differences from the all-population result.
"""
from __future__ import annotations

import csv
import io
import math
import re
import zipfile
from typing import Any

AGE_GROUP_FIELDS = {
    "all": "population",
    "65plus": "population_65plus",
    "75plus": "population_75plus",
    "85plus": "population_85plus",
}


def _number(value: Any) -> float:
    try:
        if value is None or str(value).strip() in {"", "-", "―"}:
            return 0.0
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def enrich_100m_age_weights(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """Return direct 100 m age weights already present in the source dataset."""
    result: dict[str, dict[str, float]] = {}
    for row in rows:
        mesh = str(row.get("Meshcode") or "").strip()
        if not mesh:
            continue
        total = max(0.0, _number(row.get("PopT")))
        p65 = min(total, max(0.0, _number(row.get("Pop65over"))))
        p75 = min(p65, max(0.0, _number(row.get("Pop75over"))))
        p85 = min(p75, max(0.0, _number(row.get("Pop85over"))))
        result[mesh] = {
            "population": total,
            "population_65plus": p65,
            "population_75plus": p75,
            "population_85plus": p85,
        }
    return result


def _weighted_mean(features: list[dict[str, Any]], weight_key: str, minute_key: str) -> float | None:
    numerator = 0.0
    denominator = 0.0
    for feature in features:
        props = feature.get("properties") or {}
        weight = max(0.0, _number(props.get(weight_key)))
        value = props.get(minute_key)
        if weight <= 0 or value is None:
            continue
        try:
            minutes = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(minutes):
            continue
        numerator += weight * minutes
        denominator += weight
    return None if denominator <= 0 else numerator / denominator


def group_access_metrics(
    features: list[dict[str, Any]],
    *,
    weight_key: str,
    baseline_key: str,
    disrupted_key: str,
) -> dict[str, float | None]:
    population = sum(max(0.0, _number((f.get("properties") or {}).get(weight_key))) for f in features)
    reachable_30 = 0.0
    reachable_60 = 0.0
    affected_1 = 0.0
    affected_5 = 0.0
    affected_10 = 0.0
    for feature in features:
        props = feature.get("properties") or {}
        weight = max(0.0, _number(props.get(weight_key)))
        if weight <= 0:
            continue
        before = props.get(baseline_key)
        after = props.get(disrupted_key)
        before_f = None if before is None else float(before)
        after_f = None if after is None else float(after)
        if before_f is not None and math.isfinite(before_f):
            if before_f <= 30:
                reachable_30 += weight
            if before_f <= 60:
                reachable_60 += weight
        if before_f is None or after_f is None or not (math.isfinite(before_f) and math.isfinite(after_f)):
            continue
        delta = after_f - before_f
        if delta > 1.0:
            affected_1 += weight
        if delta > 5.0:
            affected_5 += weight
        if delta > 10.0:
            affected_10 += weight

    baseline_mean = _weighted_mean(features, weight_key, baseline_key)
    disrupted_mean = _weighted_mean(features, weight_key, disrupted_key)
    mean_change = None if baseline_mean is None or disrupted_mean is None else disrupted_mean - baseline_mean

    def share(value: float) -> float | None:
        return None if population <= 0 else 100.0 * value / population

    return {
        "population": round(population, 4),
        "baseline_reachable_30min": round(reachable_30, 4),
        "baseline_reachable_60min": round(reachable_60, 4),
        "affected_gt1min": round(affected_1, 4),
        "affected_gt5min": round(affected_5, 4),
        "affected_gt10min": round(affected_10, 4),
        "affected_share_gt1min_pct": None if share(affected_1) is None else round(share(affected_1), 3),
        "affected_share_gt5min_pct": None if share(affected_5) is None else round(share(affected_5), 3),
        "affected_share_gt10min_pct": None if share(affected_10) is None else round(share(affected_10), 3),
        "baseline_weighted_mean_minutes": None if baseline_mean is None else round(baseline_mean, 3),
        "disrupted_weighted_mean_minutes": None if disrupted_mean is None else round(disrupted_mean, 3),
        "mean_minutes_change": None if mean_change is None else round(mean_change, 3),
    }


def equity_gaps(groups: dict[str, dict[str, float | None]]) -> dict[str, dict[str, float | None]]:
    """Difference from all-population result; positive means larger burden."""
    overall = groups["all"]
    result: dict[str, dict[str, float | None]] = {}
    for group in ("65plus", "75plus", "85plus"):
        current = groups[group]
        a = current.get("affected_share_gt1min_pct")
        b = overall.get("affected_share_gt1min_pct")
        mc = current.get("mean_minutes_change")
        mb = overall.get("mean_minutes_change")
        result[group] = {
            "affected_share_gt1min_gap_pp": None if a is None or b is None else round(float(a) - float(b), 3),
            "mean_minutes_change_gap": None if mc is None or mb is None else round(float(mc) - float(mb), 3),
        }
    return result


def decode_official_region_age_zip(payload: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Decode Ozu's latest region/age CSV from its ZIP without persisting raw rows."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not names:
            raise ValueError("official Ozu age population ZIP has no CSV")
        raw = archive.read(names[0])
    text = None
    for encoding in ("utf-8-sig", "cp932", "shift_jis"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            pass
    if text is None:
        raise ValueError("official Ozu age population CSV cannot be decoded")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("official Ozu age population CSV has no header")
    return list(reader.fieldnames), list(reader)


def official_region_age_context(payload: bytes) -> dict[str, Any]:
    """Aggregate official 2026 region rows for context only, not grid allocation."""
    headers, rows = decode_official_region_age_zip(payload)
    required = {"地域コード", "地域名", "総人口", "調査年月日"}
    if not required.issubset(set(headers)):
        raise ValueError("official Ozu age population schema changed")

    # Current source uses sex-specific five-year bands such as 65-69歳の男性.
    # Also accept a final N歳以上 band if present.
    age_columns: dict[str, int] = {}
    for header in headers:
        match = re.match(r"^(\d+)(?:-\d+)?歳(?:以上)?の(?:男性|女性)$", header.strip())
        if match:
            age_columns[header] = int(match.group(1))
    if not age_columns:
        raise ValueError("official Ozu age population age-band columns not found")

    total = 0.0
    age_sums = {65: 0.0, 75: 0.0, 85: 0.0}
    valid_regions = 0
    dates: set[str] = set()
    for row in rows:
        region = str(row.get("地域コード") or "").strip()
        if not region:
            continue
        total += max(0.0, _number(row.get("総人口")))
        valid_regions += 1
        date = str(row.get("調査年月日") or "").strip()
        if date:
            dates.add(date)
        for threshold in age_sums:
            age_sums[threshold] += sum(
                max(0.0, _number(row.get(column)))
                for column, lower in age_columns.items()
                if lower >= threshold
            )
    if valid_regions < 1 or total <= 0:
        raise ValueError("official Ozu age population has no usable region rows")

    return {
        "region_rows": valid_regions,
        "dates": sorted(dates),
        "population": round(total, 4),
        "population_65plus": round(age_sums[65], 4),
        "population_75plus": round(age_sums[75], 4),
        "population_85plus": round(age_sums[85], 4),
        "share_65plus_pct": round(100.0 * age_sums[65] / total, 3),
        "share_75plus_pct": round(100.0 * age_sums[75] / total, 3),
        "share_85plus_pct": round(100.0 * age_sums[85] / total, 3),
        "age_band_columns": len(age_columns),
    }
