from accessibility.official_facilities import normalize_facility_name, verify_osm_hospitals


def test_normalize_facility_name_removes_legal_prefix_and_width():
    assert normalize_facility_name("医療法人　北斗会 大洲中央病院") == "北斗会大洲中央病院"
    assert normalize_facility_name("ＨＩＴＯ病院") == "hito病院"


def test_named_osm_hospital_requires_name_and_proximity():
    osm = [
        {"id": "osm-1", "name": "北斗会大洲中央病院", "lat": 33.50, "lon": 132.54},
        {"id": "osm-2", "name": "別の病院", "lat": 33.50, "lon": 132.54},
    ]
    official = [
        {
            "official_id": "1",
            "official_name": "医療法人北斗会大洲中央病院",
            "short_name": "大洲中央病院",
            "lat": 33.5003,
            "lon": 132.5402,
        }
    ]
    verified, stats = verify_osm_hospitals(osm, official)
    assert [item["id"] for item in verified] == ["osm-1"]
    assert verified[0]["officially_verified"] is True
    assert "official_name" not in verified[0]
    assert stats["verified_osm_hospitals"] == 1
    assert stats["unverified_osm_hospitals_excluded"] == 1


def test_unnamed_osm_hospital_uses_tight_spatial_gate():
    osm = [
        {"id": "near", "name": "hospital", "lat": 33.5002, "lon": 132.5401},
        {"id": "far", "name": "hospital", "lat": 33.5030, "lon": 132.5400},
    ]
    official = [
        {
            "official_id": "1",
            "official_name": "市立大洲病院",
            "short_name": "市立大洲病院",
            "lat": 33.5000,
            "lon": 132.5400,
        }
    ]
    verified, stats = verify_osm_hospitals(osm, official)
    assert [item["id"] for item in verified] == ["near"]
    assert stats["verified_osm_hospitals"] == 1
