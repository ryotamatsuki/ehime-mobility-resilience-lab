from accessibility.official_shelters import (
    match_official_shelters,
    normalize_address,
    normalize_shelter_name,
)


def test_normalize_shelter_name_handles_fullwidth_and_punctuation():
    assert normalize_shelter_name(" 大洲小学校（運動場） ") == "大洲小学校運動場"


def test_normalize_address_removes_city_prefix_and_banchi_wording():
    assert normalize_address("愛媛県大洲市大洲711番地") == "大洲711-"


def test_match_accepts_clean_osm_name_inside_official_furigana_contaminated_name():
    official = {
        "welfare": [
            {
                "official_id": "welfare:1",
                "kind": "welfare",
                "name": "多機能型事業所あいわ苑タキノウガタジギョウショエン",
                "address": "大洲660番地1",
            }
        ]
    }
    candidates = [
        {
            "id": "osm:node:1",
            "name": "多機能型事業所あいわ苑",
            "address": "",
            "lat": 33.5,
            "lon": 132.54,
        }
    ]
    matched, stats = match_official_shelters(official, candidates)
    assert len(matched["welfare"]) == 1
    assert matched["welfare"][0]["location_match_method"] == "osm_name_in_official"
    assert matched["welfare"][0]["location_match_quality"] == "name_equivalent"
    assert stats["by_kind"]["welfare"]["matched_records"] == 1


def test_school_ground_matched_to_parent_school_is_explicitly_parent_feature():
    official = {
        "emergency": [
            {
                "official_id": "emergency:7",
                "kind": "emergency",
                "name": "県立大洲高等学校運動場",
                "address": "大洲737番地",
            }
        ]
    }
    candidates = [
        {
            "id": "osm:way:7",
            "name": "県立大洲高等学校",
            "address": "",
            "lat": 33.506,
            "lon": 132.545,
        }
    ]
    matched, stats = match_official_shelters(official, candidates)
    assert len(matched["emergency"]) == 1
    assert matched["emergency"][0]["location_match_quality"] == "parent_feature"
    assert stats["by_kind"]["emergency"]["match_quality"]["parent_feature"] == 1


def test_match_rejects_ambiguous_equal_name_candidates():
    official = {
        "general": [
            {
                "official_id": "general:1",
                "kind": "general",
                "name": "大洲小学校",
                "address": "大洲711番地",
            }
        ]
    }
    candidates = [
        {"id": "osm:node:1", "name": "大洲小学校", "address": "", "lat": 33.5, "lon": 132.54},
        {"id": "osm:way:2", "name": "大洲小学校", "address": "", "lat": 33.5001, "lon": 132.5401},
    ]
    matched, stats = match_official_shelters(official, candidates)
    assert matched["general"] == []
    assert stats["by_kind"]["general"]["ambiguous_records"] == 1
