from scripts.build_network.a1_13_sensitivity import (
    SENSITIVITY_CASES,
    aggregate_candidate_ranking,
    direction,
    direction_stability,
    reference_stability,
    scale_minutes,
    validate_cases,
)


def test_pre_registered_cases_are_stable_and_complete():
    validate_cases()
    assert [case.id for case in SENSITIVITY_CASES] == [
        "baseline",
        "walk_speed_3_6",
        "walk_speed_1_8",
        "access_walk_10",
        "access_walk_30",
        "transfer_walk_5",
        "transfer_walk_15",
    ]
    assert len(SENSITIVITY_CASES) == 7


def test_uniform_walk_speed_scaling_is_exact_ratio():
    assert scale_minutes(10.0, 4.8) == 10.0
    assert scale_minutes(10.0, 2.4) == 20.0
    assert scale_minutes(10.0, 1.8) == 10.0 * 4.8 / 1.8


def test_aggregate_candidate_ranking_uses_worst_daily_event():
    rows = [
        {
            "departure_time": "08:00",
            "departure_seconds": 8 * 3600,
            "route_ranking": [
                {
                    "id": "A",
                    "evaluated": True,
                    "impact": {
                        "population_with_gt_1min_increase": 10,
                        "mean_minutes_change": 0.5,
                    },
                },
                {
                    "id": "B",
                    "evaluated": True,
                    "impact": {
                        "population_with_gt_1min_increase": 20,
                        "mean_minutes_change": 0.2,
                    },
                },
            ],
        },
        {
            "departure_time": "11:00",
            "departure_seconds": 11 * 3600,
            "route_ranking": [
                {
                    "id": "A",
                    "evaluated": True,
                    "impact": {
                        "population_with_gt_1min_increase": 30,
                        "mean_minutes_change": 0.8,
                    },
                },
                {
                    "id": "B",
                    "evaluated": True,
                    "impact": {
                        "population_with_gt_1min_increase": 21,
                        "mean_minutes_change": 0.3,
                    },
                },
            ],
        },
    ]
    ranking = aggregate_candidate_ranking(rows, "route_ranking")
    assert [item["id"] for item in ranking] == ["A", "B"]
    assert ranking[0]["peak_departure_time"] == "11:00"
    assert ranking[0]["rank"] == 1


def test_reference_stability_reports_top1_and_top3_without_score():
    case_rankings = {
        "baseline": [
            {"id": "A", "rank": 1, "impact": {}, "peak_departure_time": "11:00"},
            {"id": "B", "rank": 2, "impact": {}, "peak_departure_time": "10:00"},
        ],
        "case2": [
            {"id": "B", "rank": 1, "impact": {}, "peak_departure_time": "10:00"},
            {"id": "A", "rank": 2, "impact": {}, "peak_departure_time": "12:00"},
        ],
        "case3": [
            {"id": "B", "rank": 1, "impact": {}, "peak_departure_time": "10:00"},
            {"id": "C", "rank": 2, "impact": {}, "peak_departure_time": "09:00"},
            {"id": "D", "rank": 3, "impact": {}, "peak_departure_time": "08:00"},
            {"id": "A", "rank": 4, "impact": {}, "peak_departure_time": "13:00"},
        ],
    }
    result = reference_stability(case_rankings, top_k=3)
    assert result["reference_id"] == "A"
    assert result["top1_count"] == 1
    assert result["top3_count"] == 2
    assert result["changed_top1_cases"] == ["case2", "case3"]
    assert result["outside_top_k_cases"] == ["case3"]
    assert "score" not in result


def test_direction_uses_display_precision_tolerance():
    assert direction(0.001) == "positive"
    assert direction(0.0004) == "neutral"
    assert direction(-0.0004) == "neutral"
    assert direction(-0.001) == "negative"
    assert direction(None) == "unknown"


def test_direction_stability_lists_boundary_case():
    result = direction_stability(
        {
            "baseline": 1.2,
            "same": 0.3,
            "boundary": -0.2,
        }
    )
    assert result["reference_direction"] == "positive"
    assert result["same_direction_count"] == 2
    assert result["changed_direction_cases"] == ["boundary"]
