from accessibility.multimodal import earliest_arrival_minutes, mesh100m_center, summarize_population_access


def test_mesh100m_center_is_in_expected_ozu_area():
    lat, lon = mesh100m_center("5032137924")
    assert 33.47 < lat < 33.49
    assert 132.49 < lon < 132.51


def test_connection_scan_uses_transit_when_faster_than_direct_walk():
    value = earliest_arrival_minutes(
        zone_node="zone",
        departure_seconds=8 * 3600,
        connections=[
            {
                "trip_id": "t1",
                "from_stop": "s1",
                "to_stop": "s2",
                "departure_seconds": 8 * 3600 + 5 * 60,
                "arrival_seconds": 8 * 3600 + 15 * 60,
            }
        ],
        trip_routes={"t1": "r1"},
        stop_walk={"s1": {"zone": 3.0}, "s2": {"zone": 99.0}},
        facility_walk_by_node={"zone": 40.0, "n1": 30.0, "n2": 4.0},
        stop_nodes={"s1": "n1", "s2": "n2"},
    )
    assert value == 19.0


def test_connection_scan_respects_disabled_route():
    value = earliest_arrival_minutes(
        zone_node="zone",
        departure_seconds=8 * 3600,
        connections=[
            {
                "trip_id": "t1",
                "from_stop": "s1",
                "to_stop": "s2",
                "departure_seconds": 8 * 3600 + 5 * 60,
                "arrival_seconds": 8 * 3600 + 15 * 60,
            }
        ],
        trip_routes={"t1": "r1"},
        stop_walk={"s1": {"zone": 3.0}, "s2": {"zone": 99.0}},
        facility_walk_by_node={"zone": 40.0, "n1": 30.0, "n2": 4.0},
        stop_nodes={"s1": "n1", "s2": "n2"},
        disabled_routes={"r1"},
    )
    assert value == 40.0


def test_population_summary_uses_weighted_population():
    zones = [
        {"zone_id": "a", "population": 100.0},
        {"zone_id": "b", "population": 50.0},
    ]
    result = summarize_population_access(zones, {"a": 20.0, "b": 70.0})
    assert result["reachable_30min"] == 100.0
    assert result["reachable_60min"] == 100.0
    assert result["reachable_90min"] == 150.0
    assert result["population_weighted_mean_minutes"] == 36.667
