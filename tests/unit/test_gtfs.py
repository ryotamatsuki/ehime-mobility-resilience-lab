from datetime import date
from pathlib import Path
import unittest

from transit.gtfs import GTFSFeed, parse_gtfs_time


FIXTURE = Path(__file__).parents[1] / "fixtures" / "gtfs" / "mini_ehime"


class GTFSTests(unittest.TestCase):
    def test_gtfs_validation_and_24_hour_time(self):
        feed = GTFSFeed.from_directory(FIXTURE, feed_id="fixture")
        self.assertEqual(feed.validate(), [])
        self.assertEqual(parse_gtfs_time("25:00:00"), 90000)
        self.assertEqual(len(feed.connections(date(2026, 8, 25))), 2)
        self.assertEqual(feed.connections(date(2026, 8, 24)), [])
        geojson = feed.route_geojson()
        self.assertEqual(geojson["features"][0]["properties"]["shape_source"], "official_shape")
