import unittest
from app import app
from services.catalog import varieties

class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)

    def test_catalog(self):
        response = self.client.get("/api/catalog")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["varieties"])

    def test_check(self):
        slug = varieties()[0]["slug"]
        response = self.client.post("/api/planner", json={
            "mode": "check", "variety": slug, "soil": "loam", "season": "Spring"
        })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertIn("improvements", response.get_json()["result"])

    def test_invalid_soil(self):
        response = self.client.post("/api/planner", json={"soil": "invalid"})
        self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main()
