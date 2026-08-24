from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import AgentProfile, Order, User, UserRole, OrderStatus, OrderTrackingHistory, AgentStatus
from app.schemas import AgentProfileOut, AgentProfileUpdate, OrderAssignAgentRequest, OrderOut
from app.routers.auth import get_current_user, require_roles
from app.assignment_engine import auto_assign_agent_to_order
from app.notification_engine import notify_order_status_change

router = APIRouter(prefix="/api/agents", tags=["Agent Operations"])

@router.get("", response_model=List[AgentProfileOut])
def list_agents(db: Session = Depends(get_db), current_user=Depends(require_roles([UserRole.ADMIN, UserRole.AGENT]))):
    agents = db.query(AgentProfile).all()
    out = []
    for a in agents:
        out.append(AgentProfileOut(
            id=a.id,
            user_id=a.user.id,
            user_name=a.user.name,
            user_email=a.user.email,
            user_phone=a.user.phone,
            status=a.status,
            current_lat=a.current_lat,
            current_lng=a.current_lng,
            active_zone_id=a.active_zone_id,
            active_zone_name=a.active_zone.name if a.active_zone else None,
            current_workload=a.current_workload
        ))
    return out

@router.put("/me", response_model=AgentProfileOut)
def update_my_agent_profile(
    update_in: AgentProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.AGENT]))
):
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == current_user.id).first()
    if not profile:
        profile = AgentProfile(user_id=current_user.id)
        db.add(profile)

    if update_in.status:
        st = update_in.status.upper()
        if st in [AgentStatus.AVAILABLE, AgentStatus.ON_DELIVERY, AgentStatus.OFFLINE]:
            profile.status = st

    if update_in.current_lat is not None:
        profile.current_lat = update_in.current_lat
    if update_in.current_lng is not None:
        profile.current_lng = update_in.current_lng
    if update_in.active_zone_id is not None:
        profile.active_zone_id = update_in.active_zone_id

    db.commit()
    db.refresh(profile)

    return AgentProfileOut(
        id=profile.id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_email=current_user.email,
        user_phone=current_user.phone,
        status=profile.status,
        current_lat=profile.current_lat,
        current_lng=profile.current_lng,
        active_zone_id=profile.active_zone_id,
        active_zone_name=profile.active_zone.name if profile.active_zone else None,
        current_workload=profile.current_workload
    )

@router.post("/assign-manual/{order_id}")
def manual_assign_agent(
    order_id: int,
    req: OrderAssignAgentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    agent_user = db.query(User).filter(User.id == req.agent_id, User.role == UserRole.AGENT).first()
    if not agent_user:
        raise HTTPException(status_code=400, detail="Invalid agent_id. User is not an Agent.")

    old_agent_id = order.agent_id
    order.agent_id = agent_user.id
    old_status = order.status
    order.status = OrderStatus.ASSIGNED

    # Update workloads
    if old_agent_id:
        old_prof = db.query(AgentProfile).filter(AgentProfile.user_id == old_agent_id).first()
        if old_prof and old_prof.current_workload > 0:
            old_prof.current_workload -= 1

    new_prof = db.query(AgentProfile).filter(AgentProfile.user_id == agent_user.id).first()
    if new_prof:
        new_prof.current_workload += 1

    # Record tracking history
    history = OrderTrackingHistory(
        order_id=order.id,
        status=OrderStatus.ASSIGNED,
        actor_id=current_user.id,
        actor_name=current_user.name,
        actor_role="ADMIN",
        notes=f"Manually assigned to Agent '{agent_user.name}' by Admin.",
        location_lat=new_prof.current_lat if new_prof else None,
        location_lng=new_prof.current_lng if new_prof else None
    )
    db.add(history)
    db.commit()

    notify_order_status_change(
        db, order=order, previous_status=old_status, new_status=OrderStatus.ASSIGNED,
        custom_notes=f"Admin manually assigned agent {agent_user.name}."
    )

    return {"message": f"Order {order.tracking_number} assigned to {agent_user.name} successfully."}

@router.post("/auto-assign/{order_id}")
def trigger_auto_assignment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    assigned_agent = auto_assign_agent_to_order(db, order, actor_id=current_user.id, actor_name=current_user.name)
    if not assigned_agent:
        raise HTTPException(status_code=400, detail="No available delivery agent found in system right now.")

    return {"message": f"Order {order.tracking_number} auto-assigned to agent {assigned_agent.name} successfully."}
