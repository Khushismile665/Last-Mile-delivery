import math
from sqlalchemy.orm import Session
from app.models import AgentProfile, Order, OrderStatus, OrderTrackingHistory, User, AgentStatus
from app.notification_engine import notify_order_status_change
from typing import Optional

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate Haversine distance between two geographical coordinates in kilometers.
    """
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Zone center coordinate lookup mapping (defaults for demo areas)
ZONE_COORDINATE_MAP = {
    "NORTH": (28.6500, 77.2100),
    "SOUTH": (28.5355, 77.2410),
    "EAST":  (28.6280, 77.2950),
    "WEST":  (28.6366, 77.1000),
    "CENTRAL": (28.6139, 77.2090)
}

def get_order_pickup_coords(order: Order) -> tuple[float, float]:
    """
    Returns approximate (lat, lng) for pickup location.
    Defaults to Central Zone coordinates if custom coords not specified.
    """
    if order.pickup_zone and order.pickup_zone.code:
        zone_key = order.pickup_zone.code.split("-")[0].upper()
        if zone_key in ZONE_COORDINATE_MAP:
            return ZONE_COORDINATE_MAP[zone_key]
    return (28.6139, 77.2090)

def auto_assign_agent_to_order(db: Session, order: Order, actor_id: Optional[int] = None, actor_name: str = "System Auto-Assigner") -> Optional[User]:
    """
    Intelligent Auto-Assignment Logic:
    1. Fetch all agents with status 'AVAILABLE'.
    2. Score each agent based on:
       - Haversine distance from agent's current location to order's pickup location.
       - Zone alignment bonus (-50 score reduction if agent's active zone matches pickup zone).
       - Current active workload penalty (+5 score per active order).
    3. Assign agent with lowest composite score.
    4. Update order status to 'ASSIGNED', record tracking history, and dispatch notification.
    """
    available_agents = db.query(AgentProfile).filter(AgentProfile.status == AgentStatus.AVAILABLE).all()

    if not available_agents:
        # No available agents in system
        return None

    pickup_lat, pickup_lng = get_order_pickup_coords(order)

    best_agent_profile = None
    lowest_score = float('inf')

    for profile in available_agents:
        # Distance calculation
        dist = haversine_distance(profile.current_lat, profile.current_lng, pickup_lat, pickup_lng)
        
        # Zone match bonus
        same_zone = (profile.active_zone_id == order.pickup_zone_id)
        zone_bonus = 50.0 if same_zone else 0.0

        # Workload penalty
        workload_penalty = profile.current_workload * 5.0

        # Composite score calculation (lower is better)
        score = dist + workload_penalty - zone_bonus

        if score < lowest_score:
            lowest_score = score
            best_agent_profile = profile

    if not best_agent_profile:
        return None

    # Perform assignment
    assigned_user = best_agent_profile.user
    order.agent_id = assigned_user.id
    old_status = order.status
    order.status = OrderStatus.ASSIGNED
    best_agent_profile.current_workload += 1

    # Record immutable tracking history
    history = OrderTrackingHistory(
        order_id=order.id,
        status=OrderStatus.ASSIGNED,
        actor_id=actor_id,
        actor_name=actor_name,
        actor_role="SYSTEM" if not actor_id else "ADMIN",
        notes=f"Auto-assigned to Agent '{assigned_user.name}' (Zone Match: {'Yes' if best_agent_profile.active_zone_id == order.pickup_zone_id else 'No'}).",
        location_lat=best_agent_profile.current_lat,
        location_lng=best_agent_profile.current_lng
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    # Dispatch notifications to Customer and Agent
    notify_order_status_change(
        db,
        order=order,
        previous_status=old_status,
        new_status=OrderStatus.ASSIGNED,
        custom_notes=f"Agent {assigned_user.name} ({assigned_user.phone or 'N/A'}) has been assigned to your order."
    )

    return assigned_user
