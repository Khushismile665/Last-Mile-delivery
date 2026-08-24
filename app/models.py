from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"

class OrderType(str, enum.Enum):
    B2B = "B2B"
    B2C = "B2C"

class RouteType(str, enum.Enum):
    INTRA = "INTRA"
    INTER = "INTER"

class PaymentType(str, enum.Enum):
    PREPAID = "PREPAID"
    COD = "COD"

class AgentStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ON_DELIVERY = "ON_DELIVERY"
    OFFLINE = "OFFLINE"

class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RESCHEDULED = "RESCHEDULED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.CUSTOMER)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer", foreign_keys="Order.customer_id")
    assigned_orders = relationship("Order", back_populates="agent", foreign_keys="Order.agent_id")
    agent_profile = relationship("AgentProfile", back_populates="user", uselist=False)

class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    areas = relationship("AreaMapping", back_populates="zone", cascade="all, delete-orphan")
    agent_profiles = relationship("AgentProfile", back_populates="active_zone")

class AreaMapping(Base):
    __tablename__ = "area_mappings"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    pincode = Column(String(10), index=True, nullable=False)
    area_name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False, default="Metro City")

    zone = relationship("Zone", back_populates="areas")

class RateCard(Base):
    __tablename__ = "rate_cards"

    id = Column(Integer, primary_key=True, index=True)
    order_type = Column(String(10), nullable=False)  # B2B, B2C
    route_type = Column(String(10), nullable=False)  # INTRA, INTER
    base_rate = Column(Float, nullable=False, default=50.0)
    per_kg_rate = Column(Float, nullable=False, default=15.0)
    min_charge = Column(Float, nullable=False, default=60.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class CODSurcharge(Base):
    __tablename__ = "cod_surcharges"

    id = Column(Integer, primary_key=True, index=True)
    order_type = Column(String(10), unique=True, nullable=False)  # B2B, B2C
    fixed_fee = Column(Float, nullable=False, default=20.0)
    percentage_fee = Column(Float, nullable=False, default=2.0)

class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    current_lat = Column(Float, nullable=False, default=28.6139)
    current_lng = Column(Float, nullable=False, default=77.2090)
    active_zone_id = Column(Integer, ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default=AgentStatus.AVAILABLE)
    current_workload = Column(Integer, default=0)

    user = relationship("User", back_populates="agent_profile")
    active_zone = relationship("Zone", back_populates="agent_profiles")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(40), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    pickup_address = Column(Text, nullable=False)
    pickup_pincode = Column(String(10), nullable=False)
    pickup_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)

    drop_address = Column(Text, nullable=False)
    drop_pincode = Column(String(10), nullable=False)
    drop_zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)

    length_cm = Column(Float, nullable=False)
    width_cm = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    actual_weight_kg = Column(Float, nullable=False)
    volumetric_weight_kg = Column(Float, nullable=False)
    billable_weight_kg = Column(Float, nullable=False)

    order_type = Column(String(10), nullable=False)  # B2B, B2C
    payment_type = Column(String(10), nullable=False)  # PREPAID, COD

    base_charge = Column(Float, nullable=False)
    weight_charge = Column(Float, nullable=False)
    cod_surcharge = Column(Float, nullable=False, default=0.0)
    total_charge = Column(Float, nullable=False)

    status = Column(String(30), nullable=False, default=OrderStatus.CREATED)
    failure_reason = Column(Text, nullable=True)
    rescheduled_date = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("User", foreign_keys=[customer_id], back_populates="orders")
    agent = relationship("User", foreign_keys=[agent_id], back_populates="assigned_orders")
    pickup_zone = relationship("Zone", foreign_keys=[pickup_zone_id])
    drop_zone = relationship("Zone", foreign_keys=[drop_zone_id])
    history = relationship("OrderTrackingHistory", back_populates="order", cascade="all, delete-orphan", order_by="OrderTrackingHistory.timestamp.asc()")

class OrderTrackingHistory(Base):
    __tablename__ = "order_tracking_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), nullable=False)
    actor_id = Column(Integer, nullable=True)
    actor_name = Column(String(100), nullable=False)
    actor_role = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="history")

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True)
    recipient_email = Column(String(120), nullable=False)
    recipient_phone = Column(String(20), nullable=True)
    channel = Column(String(10), nullable=False, default="EMAIL")
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="SENT")
