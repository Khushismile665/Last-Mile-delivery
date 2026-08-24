import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Use single shared in-memory SQLite pool for isolated test suite
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestLastMileDeliveryTracker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        # Seed test db
        from app.models import User, UserRole, Zone, AreaMapping, RateCard, CODSurcharge, AgentProfile, AgentStatus
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        
        # Seed admin, customer, agent
        admin = User(name="Test Admin", email="testadmin@delivery.com", password_hash=pwd.hash("pass"), role=UserRole.ADMIN)
        cust = User(name="Test Customer", email="testcust@example.com", password_hash=pwd.hash("pass"), role=UserRole.CUSTOMER)
        agent = User(name="Test Agent", email="testagent@delivery.com", password_hash=pwd.hash("pass"), role=UserRole.AGENT)
        db.add_all([admin, cust, agent])
        db.commit()

        # Seed Zone & Area
        z1 = Zone(name="North Zone", code="NORTH-01")
        z2 = Zone(name="South Zone", code="SOUTH-01")
        db.add_all([z1, z2])
        db.commit()

        a1 = AreaMapping(zone_id=z1.id, pincode="110001", area_name="Connaught Place", city="Delhi")
        a2 = AreaMapping(zone_id=z2.id, pincode="110016", area_name="Hauz Khas", city="Delhi")
        db.add_all([a1, a2])

        # Agent profile
        ap = AgentProfile(user_id=agent.id, active_zone_id=z1.id, status=AgentStatus.AVAILABLE, current_lat=28.65, current_lng=77.21)
        db.add(ap)

        # Rate Cards
        rc1 = RateCard(order_type="B2C", route_type="INTRA", base_rate=40.0, per_kg_rate=15.0, min_charge=50.0)
        rc2 = RateCard(order_type="B2C", route_type="INTER", base_rate=70.0, per_kg_rate=25.0, min_charge=80.0)
        cod1 = CODSurcharge(order_type="B2C", fixed_fee=20.0, percentage_fee=1.5)
        db.add_all([rc1, rc2, cod1])
        db.commit()
        db.close()

        cls.client = TestClient(app)

    def login(self, email, password):
        res = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(res.status_code, 200, f"Login failed for {email}: {res.text}")
        return res.json()["access_token"]

    def test_01_rate_calculator(self):
        # 30 x 20 x 15 = 9000 -> 9000/5000 = 1.8 kg (volumetric) vs 1.0 kg actual -> billable = 1.8 kg
        # Intra-zone B2C -> Base 40 + (1.8 * 15) = 40 + 27 = 67.0
        payload = {
            "pickup_pincode": "110001",
            "drop_pincode": "110001",
            "length_cm": 30.0,
            "width_cm": 20.0,
            "height_cm": 15.0,
            "actual_weight_kg": 1.0,
            "order_type": "B2C",
            "payment_type": "PREPAID"
        }
        res = self.client.post("/api/rates/calculate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["volumetric_weight_kg"], 1.8)
        self.assertEqual(data["billable_weight_kg"], 1.8)
        self.assertEqual(data["route_type"], "INTRA")
        self.assertEqual(data["total_charge"], 67.0)

    def test_02_create_order_and_auto_assign(self):
        token = self.login("testcust@example.com", "pass")
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "pickup_address": "Block A Connaught Place",
            "pickup_pincode": "110001",
            "drop_address": "B-12 Hauz Khas",
            "drop_pincode": "110016",
            "length_cm": 20.0,
            "width_cm": 20.0,
            "height_cm": 10.0,
            "actual_weight_kg": 2.0,
            "order_type": "B2C",
            "payment_type": "COD"
        }
        res = self.client.post("/api/orders", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["tracking_number"].startswith("ORD-"))
        self.assertEqual(data["status"], "ASSIGNED")
        self.assertIsNotNone(data["agent_id"])

        order_id = data["id"]

        # Agent updates status to FAILED
        agent_token = self.login("testagent@delivery.com", "pass")
        agent_headers = {"Authorization": f"Bearer {agent_token}"}
        
        fail_res = self.client.put(f"/api/orders/{order_id}/status", json={
            "status": "FAILED",
            "failure_reason": "Customer phone out of coverage area"
        }, headers=agent_headers)
        self.assertEqual(fail_res.status_code, 200)
        fail_data = fail_res.json()
        self.assertEqual(fail_data["status"], "FAILED")
        self.assertEqual(fail_data["failure_reason"], "Customer phone out of coverage area")

        # Customer Reschedules delivery
        resched_res = self.client.post(f"/api/orders/{order_id}/reschedule", json={
            "rescheduled_date": "2026-08-26",
            "notes": "Deliver in afternoon"
        }, headers=headers)
        self.assertEqual(resched_res.status_code, 200)
        resched_data = resched_res.json()
        self.assertEqual(resched_data["status"], "ASSIGNED") # Auto reassigned after reschedule!
        self.assertEqual(resched_data["rescheduled_date"], "2026-08-26")

        # Verify tracking history entries
        self.assertGreaterEqual(len(resched_data["history"]), 4)

if __name__ == "__main__":
    unittest.main()
