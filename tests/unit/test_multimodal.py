from accessibility.multimodal import (
    earliest_arrival_minutes,
    mesh100m_center,
    stop_transfer_edges,
    summarize_population_access,
)


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
        # Keep the synthetic walk distances internally consistent: walking via
        # s1 must not be shorter than the declared direct 40-minute path.
        facility_walk_by_node={"zone": 40.0, "n1": 50.0, "n2": 4.0},
        stop_nodes={"s1": "n1", "s2": "n2"},
        disabled_routes={"r1"},
    )
    assert value == 40.0


def test_stop_transfer_edges_respect_network_threshold_and_buffer():
    stop_walk = {
        "s1": {"n1": 0.0, "n2": 4.5, "n3": 11.0},
        "s2": {"n1": 4.5, "n2": 0.0, "n3": 7.0},
        "s3": {"n1": 11.0, "n2": 7.0, "n3": 0.0},
    }
    stop_nodes = {"s1": "n1", "s2": "n2", "s3": "n3"}
    transfers = stop_transfer_edges(
        stop_walk,
        stop_nodes,
        max_walk_minutes=10.0,
        transfer_buffer_minutes=1.0,
    )
    assert transfers["s1"] == [
        {"to_stop": "s2", "walk_minutes": 4.5, "transfer_minutes": 5.5}
    ]
    assert {edge["to_stop"] for edge in transfers["s2"]} == {"s1", "s3"}
    assert all(edge["to_stop"] != "s1" for edge in transfers.get("s1", [])[1:])


def test_connection_scan_can_board_second_trip_after_walking_transfer():
    connections = [
        {
            "trip_id": "t1",
            "from_stop": "s1",
            "to_stop": "s2",
            "departure_seconds": 8 * 3600 + 5 * 60,
            "arrival_seconds": 8 * 3600 + 10 * 60,
        },
        {
            "trip_id": "t2",
            "from_stop": "s3",
            "to_stop": "s4",
            "departure_seconds": 8 * 3600 + 16 * 60,
            "arrival_seconds": 8 * 3600 + 25 * 60,
        },
    ]
    common = dict(
        zone_node="zone",
        departure_seconds=8 * 3600,
        connections=connections,
        trip_routes={"t1": "r1", "t2": "r2"},
        stop_walk={
            "s1": {"zone": 2.0},
            "s2": {"zone": 99.0},
            "s3": {"zone": 99.0},
            "s4": {"zone": 99.0},
        },
        facility_walk_by_node={
            "zone": 60.0,
            "n1": 60.0,
            "n2": 60.0,
            "n3": 60.0,
            "n4": 3.0,
        },
        stop_nodes={"s1": "n1", "s2": "n2", "s3": "n3", "s4": "n4"},
    )
    without_transfer = earliest_arrival_minutes(**common)
    with_transfer = earliest_arrival_minutes(
        **common,
        stop_transfers={
            "s2": [
                {"to_stop": "s3", "walk_minutes": 4.0, "transfer_minutes": 5.0}
            ]
        },
    )
    assert without_transfer == 60.0
    assert with_transfer == 28.0


def test_walking_transfer_does_not_override_disabled_second_route():
    value = earliest_arrival_minutes(
        zone_node="zone",
        departure_seconds=8 * 3600,
        connections=[
            {
                "trip_id": "t1",
                "from_stop": "s1",
                "to_stop": "s2",
                "departure_seconds": 8 * 3600 + 5 * 60,
                "arrival_seconds": 8 * 3600 + 10 * 60,
            },
            {
                "trip_id": "t2",
                "from_stop": "s3",
                "to_stop": "s4",
                "departure_seconds": 8 * 3600 + 16 * 60,
                "arrival_seconds": 8 * 3600 + 25 * 60,
            },
        ],
        trip_routes={"t1": "r1", "t2": "r2"},
        stop_walk={
            "s1": {"zone": 2.0},
            "s2": {"zone": 99.0},
            "s3": {"zone": 99.0},
            "s4": {"zone": 99.0},
        },
        facility_walk_by_node={"zone": 60.0, "n1": 60.0, "n2": 60.0, "n3": 60.0, "n4": 3.0},
        stop_nodes={"s1": "n1", "s2": "n2", "s3": "n3", "s4": "n4"},
        disabled_routes={"r2"},
        stop_transfers={
            "s2": [
                {"to_stop": "s3", "walk_minutes": 4.0, "transfer_minutes": 5.0}
            ]
        },
    )
    assert value == 60.0


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
