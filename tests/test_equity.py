from accessibility.equity import enrich_100m_age_weights, equity_gaps, group_access_metrics


def test_age_weights_are_monotone():
    rows = [{
        "Meshcode": "x", "PopT": "10", "Pop65over": "6", "Pop75over": "4", "Pop85over": "2",
    }]
    weights = enrich_100m_age_weights(rows)["x"]
    assert weights["population"] == 10
    assert weights["population_65plus"] == 6
    assert weights["population_75plus"] == 4
    assert weights["population_85plus"] == 2


def test_group_metrics_and_gap_are_transparent():
    features = [
        {"properties": {"population": 10, "population_65plus": 6, "baseline": 20, "disrupted": 25}},
        {"properties": {"population": 10, "population_65plus": 2, "baseline": 20, "disrupted": 20}},
    ]
    overall = group_access_metrics(features, weight_key="population", baseline_key="baseline", disrupted_key="disrupted")
    old = group_access_metrics(features, weight_key="population_65plus", baseline_key="baseline", disrupted_key="disrupted")
    assert overall["affected_gt1min"] == 10
    assert overall["affected_share_gt1min_pct"] == 50
    assert old["affected_gt1min"] == 6
    assert old["affected_share_gt1min_pct"] == 75
    gaps = equity_gaps({"all": overall, "65plus": old, "75plus": old, "85plus": old})
    assert gaps["65plus"]["affected_share_gt1min_gap_pp"] == 25
