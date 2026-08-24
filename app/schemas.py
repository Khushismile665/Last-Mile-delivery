from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

# --- Auth Schemas ---
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "CUSTOMER"  # CUSTOMER, AGENT, ADMIN
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# --- Zone & Area Schemas ---
class AreaMappingCreate(BaseModel):
    pincode: str
    area_name: str
    city: str = "Metro City"

class AreaMappingOut(BaseModel):
    id: int
    zone_id: int
    pincode: str
    area_name: str
    city: str

    class Config:
        from_attributes = True

class ZoneCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class ZoneOut(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    areas: List[AreaMappingOut] = []

    class Config:
        from_attributes = True

# --- Rate Card & COD Schemas ---
class RateCardCreate(BaseModel):
    order_type: str  # B2B, B2C
    route_type: str  # INTRA, INTER
    base_rate: float
    per_kg_rate: float
    min_charge: float

class RateCardOut(RateCardCreate):
    id: int

    class Config:
        from_attributes = True

class CODSurchargeCreate(BaseModel):
    order_type: str  # B2B, B2C
    fixed_fee: float
    percentage_fee: float

class CODSurchargeOut(CODSurchargeCreate):
    id: int

    class Config:
        from_attributes = True

# --- Rate Calculation Engine Schemas ---
class PriceEstimateRequest(BaseModel):
    pickup_pincode: str
    pickup_address: Optional[str] = ""
    drop_pincode: str
    drop_address: Optional[str] = ""
    length_cm: float = Field(..., gt=0)
    width_cm: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    actual_weight_kg: float = Field(..., gt=0)
    order_type: str  # B2B, B2C
    payment_type: str  # PREPAID, COD

class PriceEstimateResponse(BaseModel):
    volumetric_weight_kg: float
    actual_weight_kg: float
    billable_weight_kg: float
    pickup_zone_name: str
    pickup_zone_code: str
    drop_zone_name: str
    drop_zone_code: str
    route_type: str  # INTRA or INTER
    order_type: str
    payment_type: str
    base_charge: float
    weight_charge: float
    cod_surcharge: float
    total_charge: float
    rate_card_details: dict

# --- Agent Profile Schemas ---
class AgentProfileUpdate(BaseModel):
    status: Optional[str] = None  # AVAILABLE, ON_DELIVERY, OFFLINE
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    active_zone_id: Optional[int] = None

class AgentProfileOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    user_phone: Optional[str]
    status: str
    current_lat: float
    current_lng: float
    active_zone_id: Optional[int]
    active_zone_name: Optional[str]
    current_workload: int

    class Config:
        from_attributes = True

# --- Order Schemas ---
class OrderCreate(BaseModel):
    pickup_address: str
    pickup_pincode: str
    drop_address: str
    drop_pincode: str
    length_cm: float = Field(..., gt=0)
    width_cm: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    actual_weight_kg: float = Field(..., gt=0)
    order_type: str  # B2B, B2C
    payment_type: str  # PREPAID, COD
    customer_id: Optional[int] = None  # If created by Admin on behalf of customer

class OrderStatusUpdate(BaseModel):
    status: str  # PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED
    failure_reason: Optional[str] = None
    notes: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None

class OrderRescheduleRequest(BaseModel):
    rescheduled_date: str  # YYYY-MM-DD or readable slot string
    notes: Optional[str] = "Customer requested delivery reschedule"

class OrderAssignAgentRequest(BaseModel):
    agent_id: int

class OrderTrackingHistoryOut(BaseModel):
    id: int
    status: str
    actor_id: Optional[int]
    actor_name: str
    actor_role: str
    notes: Optional[str]
    location_lat: Optional[float]
    location_lng: Optional[float]
    timestamp: datetime

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int
    tracking_number: str
    customer_id: int
    customer_name: str
    customer_email: str
    customer_phone: Optional[str]
    agent_id: Optional[int]
    agent_name: Optional[str]
    pickup_address: str
    pickup_pincode: str
    pickup_zone_name: Optional[str]
    drop_address: str
    drop_pincode: str
    drop_zone_name: Optional[str]
    length_cm: float
    width_cm: float
    height_cm: float
    actual_weight_kg: float
    volumetric_weight_kg: float
    billable_weight_kg: float
    order_type: str
    payment_type: str
    base_charge: float
    weight_charge: float
    cod_surcharge: float
    total_charge: float
    status: str
    failure_reason: Optional[str]
    rescheduled_date: Optional[str]
    created_at: datetime
    updated_at: datetime
    history: List[OrderTrackingHistoryOut] = []

    class Config:
        from_attributes = True

# --- Notification Log Schema ---
class NotificationLogOut(BaseModel):
    id: int
    order_id: Optional[int]
    recipient_email: str
    recipient_phone: Optional[str]
    channel: str
    subject: str
    message: str
    sent_at: datetime
    status: str

    class Config:
        from_attributes = True
