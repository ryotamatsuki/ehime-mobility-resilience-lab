import json
import tempfile
import zipfile
from pathlib import Path
import unittest

from admin.update_center import DataUpdateCenter, validate_upload


class UpdateCenterTests(unittest.TestCase):
    def test_gtfs_upload_validation_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            archive = tmp_path / "feed.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                for name in ["agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]:
                    handle.writestr(name, "id\nvalue\n")
            result = validate_upload(archive)
            self.assertEqual(result["format"], "gtfs_zip")
            self.assertEqual(result["validation_status"], "passed")
            center = DataUpdateCenter(tmp_path)
            record = center.stage("fixture", archive, "2026-08-22", "test")
            self.assertEqual(record["status"], "validated")
            self.assertEqual(center.approve(record["version_id"])["status"], "active")
            self.assertTrue(json.loads((tmp_path / "data" / "metadata" / "dataset_versions.json").read_text()))

    def test_zip_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../escape.txt", "bad")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                validate_upload(archive)
