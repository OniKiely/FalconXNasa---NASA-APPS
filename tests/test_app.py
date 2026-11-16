import unittest

from app import app
from services.catalog import varieties
from services.climate import _dryness, _usgs_moisture_signal, score_climate


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)

    def test_catalog(self):
        response = self.client.get("/api/catalog")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["varieties"])

    def test_check_requires_location(self):
        slug = varieties()[0]["slug"]
        response = self.client.post("/api/planner", json={
            "mode": "check", "variety": slug, "soil": "loam", "season": "Spring"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("location", response.get_json()["error"].lower())

    def test_check_with_zip(self):
        slug = varieties()[0]["slug"]
        response = self.client.post("/api/planner", json={
            "mode": "check",
            "variety": slug,
            "soil": "loam",
            "season": "Spring",
            "postal_code": "93710",
            "city": "Fresno",
            "state": "CA",
            "country": "US",
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertIn("improvements", body["result"])
        located = body["context"]["location"]
        self.assertIsNotNone(located)
        self.assertIsInstance(located["latitude"], float)
        self.assertIsInstance(located["longitude"], float)
        self.assertTrue(body["context"]["lines"])

    def test_invalid_soil(self):
        response = self.client.post("/api/planner", json={
            "soil": "invalid", "postal_code": "93710"
        })
        self.assertEqual(response.status_code, 400)

    def test_usgs_moisture_helps_scoring(self):
        usgs = {
            "available": True,
            "observations": [{
                "kind": "groundwater",
                "value": 40,
                "distance_km": 5,
                "recent": True,
            }],
        }
        self.assertEqual(_usgs_moisture_signal(usgs), "dry")
        self.assertEqual(_dryness({}, {}, usgs), "dry")
        scored = score_climate("High; consistent moisture", "Warm season", {
            "power": {"available": False},
            "openet": {"available": False},
            "usgs": usgs,
        })
        self.assertGreater(scored["possible"], 0)
        self.assertGreater(scored["earned"], 0)


if __name__ == "__main__":
    unittest.main()
