import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from democommerce import models
from democommerce.database import Base, get_db
from democommerce.main import CATALOGUE, app
from democommerce.security import hash_password


class StoreWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)

        def override_db():
            db = self.factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        app.state.security_profile = "BASELINE"
        with self.factory() as db:
            for row in CATALOGUE:
                slug, name, category, description, price, compare, stock, featured = row
                db.add(models.Product(slug=slug, name=name, category=category, description=description,
                                      price_cents=price, compare_at_cents=compare, stock=stock, featured=featured))
            db.commit()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.state.security_profile = "BASELINE"
        self.engine.dispose()

    def register(self):
        return self.client.post("/api/auth/register", json={
            "email": "sam@example.com", "password": "Sufficient-Password-99", "full_name": "Sam Example",
        })

    def test_catalogue_and_search_are_public(self):
        response = self.client.get("/api/products?q=headphones")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertIn("Headphones", response.json()[0]["name"])

    def test_openapi_docs_are_available_with_baseline_policy(self):
        docs = self.client.get("/docs")
        self.assertEqual(docs.status_code, 200)
        self.assertIn("swagger-ui", docs.text.lower())
        self.assertIn("cdn.jsdelivr.net", docs.headers.get("content-security-policy", ""))

    def test_customer_can_register_create_order_and_see_history(self):
        registration = self.register()
        self.assertEqual(registration.status_code, 201, registration.text)
        self.assertIn("httponly", registration.headers.get("set-cookie", "").lower())
        self.assertIn("samesite=strict", registration.headers.get("set-cookie", "").lower())
        product = self.client.get("/api/products/aero-wireless-headphones").json()
        cart = self.client.post("/api/cart/items", json={"product_id": product["id"], "quantity": 1})
        self.assertEqual(cart.status_code, 200, cart.text)
        self.assertEqual(cart.json()["item_count"], 1)
        order = self.client.post("/api/orders", json={"shipping_name": "Sam Example", "shipping_address": "1 Fictional Lane, Demo City"})
        self.assertEqual(order.status_code, 201, order.text)
        self.assertTrue(order.json()["reference"].startswith("DC-"))
        self.assertIn("no payment collected", order.json()["payment_method"])
        self.assertEqual(order.json()["total_cents"], product["price_cents"])
        self.assertEqual(self.client.get("/api/orders").json()[0]["reference"], order.json()["reference"])
        self.assertEqual(self.client.get("/api/cart").json()["item_count"], 0)

    def test_customer_cannot_access_administrator_api(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.client.get("/api/admin/orders").status_code, 403)

    def test_customer_endpoints_require_authentication(self):
        self.assertEqual(self.client.get("/api/cart").status_code, 401)
        self.assertEqual(self.client.get("/api/orders").status_code, 401)

    def test_authentication_sets_baseline_headers_and_cors_is_restricted(self):
        result = self.register()
        self.assertEqual(result.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(result.headers.get("x-frame-options"), "DENY")
        denied = self.client.options("/api/products", headers={
            "Origin": "https://unapproved.example", "Access-Control-Request-Method": "GET",
        })
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_researcher_profiles_are_protected_reversible_and_audited(self):
        with self.factory() as db:
            db.add(models.User(email="researcher@example.com", full_name="Research Admin", role="admin",
                               password_hash=hash_password("Admin-Password-88")))
            db.commit()
        with patch.dict("os.environ", {"DEMO_TEST_PROFILES_ENABLED": "1"}):
            login = self.client.post("/api/auth/login", json={"email": "researcher@example.com", "password": "Admin-Password-88"})
            self.assertEqual(login.status_code, 200, login.text)
            applied = self.client.post("/api/admin/security-profile", json={"profile": "TEST_CHANGE", "note": "Controlled local experiment"})
            self.assertEqual(applied.status_code, 200, applied.text)
            self.assertEqual(applied.json()["previous_profile"], "BASELINE")
            changed = self.client.get("/api/products", headers={"Origin": "https://unapproved.example"})
            self.assertEqual(changed.headers.get("access-control-allow-origin"), "https://unapproved.example")
            self.assertEqual(changed.headers.get("access-control-allow-credentials"), "true")
            self.assertNotIn("x-frame-options", changed.headers)
            changed_login = self.client.post("/api/auth/login", json={"email": "researcher@example.com", "password": "Admin-Password-88"})
            changed_cookie = changed_login.headers.get("set-cookie", "").lower()
            self.assertNotIn("httponly", changed_cookie)
            self.assertIn("samesite=lax", changed_cookie)
            restored = self.client.post("/api/admin/security-profile", json={"profile": "RESTORED", "note": "Restore secure baseline"})
            self.assertEqual(restored.status_code, 200, restored.text)
            baseline = self.client.get("/api/products", headers={"Origin": "https://unapproved.example"})
            self.assertNotIn("access-control-allow-origin", baseline.headers)
            history = self.client.get("/api/admin/security-profile").json()["history"]
            self.assertEqual([row["profile"] for row in history[:2]], ["RESTORED", "TEST_CHANGE"])

    def test_contact_messages_are_stored_and_admin_only_for_reading(self):
        response = self.client.post("/api/contact", json={
            "name": "Test Visitor", "email": "visitor@example.com", "subject": "A product question",
            "message": "This is fictional test data for the contact workflow.",
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["reference"].startswith("MSG-"))
        self.assertEqual(self.client.get("/api/admin/contact-messages").status_code, 401)


if __name__ == "__main__":
    unittest.main()
