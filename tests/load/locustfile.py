"""
ListingJet load tests.

Usage:
    locust -f tests/load/locustfile.py --host http://localhost:8000 --headless -u 50 -r 10 -t 60s
"""
import uuid

from locust import HttpUser, between, task


class ListingJetUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        """Register and login to get a JWT token."""
        email = f"loadtest-{uuid.uuid4().hex[:8]}@example.com"
        password = "LoadTest1234"
        self.client.post("/auth/register", json={
            "email": email,
            "password": password,
            "name": "Load Test User",
        })
        resp = self.client.post("/auth/login", json={
            "email": email,
            "password": password,
        })
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}

    @task(5)
    def health_check(self):
        self.client.get("/health")

    @task(3)
    def list_listings(self):
        self.client.get("/listings", headers=self.headers)

    @task(2)
    def create_listing(self):
        resp = self.client.post("/listings", headers=self.headers, json={
            "address": {
                "street": f"{uuid.uuid4().hex[:6]} Main St",
                "city": "Denver",
                "state": "CO",
                "zip": "80201",
            },
            "metadata_": {
                "beds": 3,
                "baths": 2,
                "sqft": 1800,
                "price": 500000,
            },
        })
        if resp.status_code == 201:
            listing_id = resp.json().get("id")
            if listing_id:
                self.client.get(f"/listings/{listing_id}", headers=self.headers)

    @task(1)
    def get_me(self):
        self.client.get("/auth/me", headers=self.headers)

    @task(1)
    def demo_upload(self):
        self.client.post("/demo/upload", json={
            "photos": [
                {"url": f"https://example.com/photo{i}.jpg", "filename": f"photo{i}.jpg"}
                for i in range(5)
            ],
        })
