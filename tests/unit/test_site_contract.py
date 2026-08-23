import json

import pytest

from scripts.export_web.site_contract import (
    insert_before_recovery_card,
    merge_manifest_capabilities,
    set_ui_stage,
)


def test_set_ui_stage_adds_and_replaces_body_metadata():
    source = "<html><body><main>x</main></body></html>"
    first = set_ui_stage(source, "A1.10", destination="hospital")
    assert '<body data-ui-stage="A1.10" data-destination="hospital">' in first

    second = set_ui_stage(first, "A1.12", destination="welfare")
    assert second.count("data-ui-stage=") == 1
    assert second.count("data-destination=") == 1
    assert 'data-ui-stage="A1.12"' in second
    assert 'data-destination="welfare"' in second


def test_insert_before_recovery_card_is_idempotent():
    source = '<main><article class="analytics-card recovery-card">recovery</article></main>'
    fragment = '<article id="equity-card">equity</article>'
    first = insert_before_recovery_card(source, fragment, identity_marker='id="equity-card"')
    second = insert_before_recovery_card(first, fragment, identity_marker='id="equity-card"')
    assert first == second
    assert second.count('id="equity-card"') == 1


def test_merge_manifest_capabilities_is_idempotent_and_preserves_result_stage(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "result_stage": "A1.12",
                "analysis_result_stage": "A1.12",
                "ui_release_stage": "A1.11",
                "ui_capabilities": ["existing"],
                "artifacts": ["summary.json"],
            }
        ),
        encoding="utf-8",
    )
    for _ in range(2):
        merge_manifest_capabilities(
            path,
            result_stage="A1.12",
            ui_release_stage="A1.12",
            capabilities=["existing", "equity-gap-metrics"],
            artifacts=["summary.json", "equity_summary.json"],
        )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["result_stage"] == "A1.12"
    assert manifest["analysis_result_stage"] == "A1.12"
    assert manifest["ui_release_stage"] == "A1.12"
    assert manifest["ui_capabilities"] == ["existing", "equity-gap-metrics"]
    assert manifest["artifacts"] == ["summary.json", "equity_summary.json"]


def test_merge_manifest_rejects_result_stage_drift(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"result_stage": "A1.11"}), encoding="utf-8")
    with pytest.raises(ValueError, match="result stage changed"):
        merge_manifest_capabilities(
            path,
            result_stage="A1.12",
            ui_release_stage="A1.12",
            capabilities=[],
        )
