from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app.models import (
    User, UserRole, Zone, AreaMapping, RateCard, CODSurcharge,
    AgentProfile, AgentStatus, Order, OrderStatus, OrderTrackingHistory
)
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).filter(User.email == "admin@delivery.com").first():
            print("[Seed] Database already seeded.")
            return

        print("[Seed] Seeding database with initial data...")

        # 1. Users
        admin = User(
            name="System Admin",
            email="admin@delivery.com",
            password_hash=hash_password("Admin@123"),
            role=UserRole.ADMIN,
            phone="+91-9876543210"
        )
        customer1 = User(
            name="Rahul Sharma",
            email="customer@example.com",
            password_hash=hash_password("Customer@123"),
            role=UserRole.CUSTOMER,
            phone="+91-9811223344"
        )
        customer2 = User(
            name="Acme Enterprise Corp",
            email="acme@corp.com",
            password_hash=hash_password("Customer@123"),
            role=UserRole.CUSTOMER,
            phone="+91-9988776655"
        )

        agent_user1 = User(
            name="Vikram Singh",
            email="agent1@delivery.com",
            password_hash=hash_password("Agent@123"),
            role=UserRole.AGENT,
            phone="+91-9123456789"
        )
        agent_user2 = User(
            name="Anita Roy",
            email="agent2@delivery.com",
            password_hash=hash_password("Agent@123"),
            role=UserRole.AGENT,
            phone="+91-9234567890"
        )
        agent_user3 = User(
            name="Rajesh Kumar",
            email="agent3@delivery.com",
            password_hash=hash_password("Agent@123"),
            role=UserRole.AGENT,
            phone="+91-9345678901"
        )

        db.add_all([admin, customer1, customer2, agent_user1, agent_user2, agent_user3])
        db.commit()

        # 2. Zones & Areas
        zone_north = Zone(name="North Zone", code="NORTH-01", description="Delhi NCR North Region")
        zone_south = Zone(name="South Zone", code="SOUTH-01", description="Delhi NCR South Region")
        zone_west = Zone(name="West Zone", code="WEST-01", description="Delhi NCR West Region")
        zone_east = Zone(name="East Zone", code="EAST-01", description="Delhi NCR East Region")
        zone_central = Zone(name="Central Zone", code="CENTRAL-01", description="Central Metro Hub")

        db.add_all([zone_north, zone_south, zone_west, zone_east, zone_central])
        db.commit()

        areas = [
            AreaMapping(zone_id=zone_north.id, pincode="110001", area_name="Connaught Place", city="New Delhi"),
            AreaMapping(zone_id=zone_north.id, pincode="110007", area_name="Kamla Nagar", city="New Delhi"),
            AreaMapping(zone_id=zone_north.id, pincode="110009", area_name="Model Town", city="New Delhi"),
            
            AreaMapping(zone_id=zone_south.id, pincode="110016", area_name="Hauz Khas", city="New Delhi"),
            AreaMapping(zone_id=zone_south.id, pincode="110024", area_name="Lajpat Nagar", city="New Delhi"),
            AreaMapping(zone_id=zone_south.id, pincode="110017", area_name="Malviya Nagar", city="New Delhi"),

            AreaMapping(zone_id=zone_west.id, pincode="110018", area_name="Tilak Nagar", city="New Delhi"),
            AreaMapping(zone_id=zone_west.id, pincode="110027", area_name="Rajouri Garden", city="New Delhi"),
            AreaMapping(zone_id=zone_west.id, pincode="110015", area_name="Kirti Nagar", city="New Delhi"),

            AreaMapping(zone_id=zone_east.id, pincode="110092", area_name="Laxmi Nagar", city="New Delhi"),
            AreaMapping(zone_id=zone_east.id, pincode="110091", area_name="Mayur Vihar", city="New Delhi"),

            AreaMapping(zone_id=zone_central.id, pincode="110002", area_name="Daryaganj", city="New Delhi"),
            AreaMapping(zone_id=zone_central.id, pincode="110055", area_name="Paharganj", city="New Delhi"),
        ]
        db.add_all(areas)
        db.commit()

        # 3. Agent Profiles
        agent_profile1 = AgentProfile(
            user_id=agent_user1.id,
            active_zone_id=zone_north.id,
            current_lat=28.6500,
            current_lng=77.2100,
            status=AgentStatus.AVAILABLE,
            current_workload=1
        )
        agent_profile2 = AgentProfile(
            user_id=agent_user2.id,
            active_zone_id=zone_south.id,
            current_lat=28.5355,
            current_lng=77.2410,
            status=AgentStatus.AVAILABLE,
            current_workload=0
        )
        agent_profile3 = AgentProfile(
            user_id=agent_user3.id,
            active_zone_id=zone_west.id,
            current_lat=28.6366,
            current_lng=77.1000,
            status=AgentStatus.AVAILABLE,
            current_workload=0
        )
        db.add_all([agent_profile1, agent_profile2, agent_profile3])
        db.commit()

        # 4. Rate Cards (B2C & B2B for Intra and Inter zone)
        rate_cards = [
            RateCard(order_type="B2C", route_type="INTRA", base_rate=40.0, per_kg_rate=15.0, min_charge=50.0),
            RateCard(order_type="B2C", route_type="INTER", base_rate=70.0, per_kg_rate=25.0, min_charge=80.0),
            RateCard(order_type="B2B", route_type="INTRA", base_rate=100.0, per_kg_rate=12.0, min_charge=120.0),
            RateCard(order_type="B2B", route_type="INTER", base_rate=180.0, per_kg_rate=20.0, min_charge=200.0),
        ]
        db.add_all(rate_cards)

        # 5. COD Surcharges
        cod_surcharges = [
            CODSurcharge(order_type="B2C", fixed_fee=20.0, percentage_fee=1.5),
            CODSurcharge(order_type="B2B", fixed_fee=50.0, percentage_fee=2.5),
        ]
        db.add_all(cod_surcharges)
        db.commit()

        # 6. Sample Orders with Tracking Timelines
        # Order 1: Delivered B2C Order
        order1 = Order(
            tracking_number="ORD-2026-8801",
            customer_id=customer1.id,
            agent_id=agent_user1.id,
            pickup_address="Block B, Connaught Place, New Delhi",
            pickup_pincode="110001",
            pickup_zone_id=zone_north.id,
            drop_address="Sector 5, Kamla Nagar, New Delhi",
            drop_pincode="110007",
            drop_zone_id=zone_north.id,
            length_cm=30.0, width_cm=20.0, height_cm=15.0,
            actual_weight_kg=1.5,
            volumetric_weight_kg=1.8, # (30*20*15)/5000 = 1.8
            billable_weight_kg=1.8,
            order_type="B2C",
            payment_type="PREPAID",
            base_charge=40.0,
            weight_charge=27.0, # 1.8 * 15 = 27
            cod_surcharge=0.0,
            total_charge=67.0,
            status=OrderStatus.DELIVERED,
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        db.add(order1)
        db.commit()

        # Order 1 tracking history
        h1 = [
            OrderTrackingHistory(order_id=order1.id, status=OrderStatus.CREATED, actor_name=customer1.name, actor_role="CUSTOMER", notes="Order placed by customer", timestamp=datetime.utcnow() - timedelta(days=2)),
            OrderTrackingHistory(order_id=order1.id, status=OrderStatus.ASSIGNED, actor_name="System Assigner", actor_role="SYSTEM", notes="Assigned to Agent Vikram Singh", location_lat=28.6500, location_lng=77.2100, timestamp=datetime.utcnow() - timedelta(days=2, hours=-1)),
            OrderTrackingHistory(order_id=order1.id, status=OrderStatus.PICKED_UP, actor_name=agent_user1.name, actor_role="AGENT", notes="Package picked up from Connaught Place", location_lat=28.6328, location_lng=77.2197, timestamp=datetime.utcnow() - timedelta(days=1, hours=10)),
            OrderTrackingHistory(order_id=order1.id, status=OrderStatus.IN_TRANSIT, actor_name=agent_user1.name, actor_role="AGENT", notes="In transit to Kamla Nagar Hub", location_lat=28.6600, location_lng=77.2150, timestamp=datetime.utcnow() - timedelta(days=1, hours=5)),
            OrderTrackingHistory(order_id=order1.id, status=OrderStatus.OUT_FOR_DELIVERY, actor_name=agent_user1.name, actor_role="AGENT", notes="Agent out for final delivery attempt", location_lat=28.6800, location_lng=77.2100, timestamp=datetime.utcnow() - timedelta(hours=4)),
            OrderTrackingHistory(order_id=order1.id, status=OrderStatus.DELIVERED, actor_name=agent_user1.name, actor_role="AGENT", notes="Package handed over to recipient and signature received", location_lat=28.6820, location_lng=77.2090, timestamp=datetime.utcnow() - timedelta(hours=1))
        ]
        db.add_all(h1)

        # Order 2: Failed Delivery B2C COD Order (Ready for Reschedule testing)
        order2 = Order(
            tracking_number="ORD-2026-8802",
            customer_id=customer1.id,
            agent_id=agent_user1.id,
            pickup_address="E-Block, Connaught Place, New Delhi",
            pickup_pincode="110001",
            pickup_zone_id=zone_north.id,
            drop_address="22 Hauz Khas Village, New Delhi",
            drop_pincode="110016",
            drop_zone_id=zone_south.id,
            length_cm=40.0, width_cm=30.0, height_cm=20.0,
            actual_weight_kg=3.0,
            volumetric_weight_kg=4.8, # (40*30*20)/5000 = 4.8
            billable_weight_kg=4.8,
            order_type="B2C",
            payment_type="COD",
            base_charge=70.0,
            weight_charge=120.0, # 4.8 * 25 = 120
            cod_surcharge=22.85, # 20 + (190 * 1.5/100) = 22.85
            total_charge=212.85,
            status=OrderStatus.FAILED,
            failure_reason="Customer unavailable at delivery address during 1st attempt",
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(order2)
        db.commit()

        h2 = [
            OrderTrackingHistory(order_id=order2.id, status=OrderStatus.CREATED, actor_name=customer1.name, actor_role="CUSTOMER", notes="Order created with COD payment", timestamp=datetime.utcnow() - timedelta(days=1)),
            OrderTrackingHistory(order_id=order2.id, status=OrderStatus.ASSIGNED, actor_name="System Assigner", actor_role="SYSTEM", notes="Assigned to Agent Vikram Singh", timestamp=datetime.utcnow() - timedelta(days=1, hours=-1)),
            OrderTrackingHistory(order_id=order2.id, status=OrderStatus.OUT_FOR_DELIVERY, actor_name=agent_user1.name, actor_role="AGENT", notes="Out for delivery", location_lat=28.5400, location_lng=77.2000, timestamp=datetime.utcnow() - timedelta(hours=3)),
            OrderTrackingHistory(order_id=order2.id, status=OrderStatus.FAILED, actor_name=agent_user1.name, actor_role="AGENT", notes="Delivery Attempt Failed: Customer unavailable at delivery address during 1st attempt", location_lat=28.5400, location_lng=77.2000, timestamp=datetime.utcnow() - timedelta(hours=1))
        ]
        db.add_all(h2)

        # Order 3: Unassigned B2C Order (Ready for Auto-Assign testing)
        order3 = Order(
            tracking_number="ORD-2026-8803",
            customer_id=customer2.id,
            agent_id=None,
            pickup_address="Bandra West Commercial Complex",
            pickup_pincode="110018", # West Zone
            pickup_zone_id=zone_west.id,
            drop_address="Laxmi Nagar Main Market",
            drop_pincode="110092", # East Zone
            drop_zone_id=zone_east.id,
            length_cm=50.0, width_cm=50.0, height_cm=40.0,
            actual_weight_kg=10.0,
            volumetric_weight_kg=20.0, # (50*50*40)/5000 = 20.0
            billable_weight_kg=20.0,
            order_type="B2B",
            payment_type="PREPAID",
            base_charge=180.0,
            weight_charge=400.0, # 20 * 20 = 400
            cod_surcharge=0.0,
            total_charge=580.0,
            status=OrderStatus.CREATED,
            created_at=datetime.utcnow() - timedelta(minutes=30)
        )
        db.add(order3)
        db.commit()

        h3 = [
            OrderTrackingHistory(order_id=order3.id, status=OrderStatus.CREATED, actor_name=customer2.name, actor_role="CUSTOMER", notes="B2B Bulk shipment created", timestamp=datetime.utcnow() - timedelta(minutes=30))
        ]
        db.add_all(h3)

        db.commit()
        print("[Seed] Seeding completed successfully.")

    except Exception as e:
        print(f"[Seed] Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
