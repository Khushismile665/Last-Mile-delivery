from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

from app.database import get_db
from app.models import Order, OrderStatus, OrderTrackingHistory, User, UserRole, AgentProfile, AgentStatus, NotificationLog
from app.schemas import OrderCreate, OrderOut, OrderStatusUpdate, OrderRescheduleRequest, NotificationLogOut
from app.rate_engine import calculate_order_price
from app.assignment_engine import auto_assign_agent_to_order
from app.notification_engine import notify_order_status_change
from app.routers.auth import get_current_user, require_roles

router = APIRouter(prefix="/api/orders", tags=["Orders & Tracking"])

def format_order_response(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        tracking_number=order.tracking_number,
        customer_id=order.customer_id,
        customer_name=order.customer.name if order.customer else "Unknown",
        customer_email=order.customer.email if order.customer else "",
        customer_phone=order.customer.phone if order.customer else None,
        agent_id=order.agent_id,
        agent_name=order.agent.name if order.agent else None,
        pickup_address=order.pickup_address,
        pickup_pincode=order.pickup_pincode,
        pickup_zone_name=order.pickup_zone.name if order.pickup_zone else None,
        drop_address=order.drop_address,
        drop_pincode=order.drop_pincode,
        drop_zone_name=order.drop_zone.name if order.drop_zone else None,
        length_cm=order.length_cm,
        width_cm=order.width_cm,
        height_cm=order.height_cm,
        actual_weight_kg=order.actual_weight_kg,
        volumetric_weight_kg=order.volumetric_weight_kg,
        billable_weight_kg=order.billable_weight_kg,
        order_type=order.order_type,
        payment_type=order.payment_type,
        base_charge=order.base_charge,
        weight_charge=order.weight_charge,
        cod_surcharge=order.cod_surcharge,
        total_charge=order.total_charge,
        status=order.status,
        failure_reason=order.failure_reason,
        rescheduled_date=order.rescheduled_date,
        created_at=order.created_at,
        updated_at=order.updated_at,
        history=order.history
    )

@router.post("", response_model=OrderOut)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates an order:
    - Customer places for themselves, or Admin creates on behalf of customer_id
    - Calculates volumetric weight & billable weight
    - Applies zone rate card and COD surcharge dynamically
    - Generates unique tracking number
    - Attempts auto-assignment to nearest available agent
    """
    target_customer_id = current_user.id
    if current_user.role == UserRole.ADMIN and order_in.customer_id:
        cust = db.query(User).filter(User.id == order_in.customer_id).first()
        if not cust:
            raise HTTPException(status_code=400, detail="Customer specified by Admin not found.")
        target_customer_id = cust.id

    # Rate Engine Calculation
    pricing = calculate_order_price(
        db=db,
        pickup_pincode=order_in.pickup_pincode,
        pickup_address=order_in.pickup_address,
        drop_pincode=order_in.drop_pincode,
        drop_address=order_in.drop_address,
        length_cm=order_in.length_cm,
        width_cm=order_in.width_cm,
        height_cm=order_in.height_cm,
        actual_weight_kg=order_in.actual_weight_kg,
        order_type=order_in.order_type,
        payment_type=order_in.payment_type
    )

    tracking_num = f"ORD-{datetime.utcnow().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"

    order = Order(
        tracking_number=tracking_num,
        customer_id=target_customer_id,
        pickup_address=order_in.pickup_address,
        pickup_pincode=order_in.pickup_pincode,
        pickup_zone_id=pricing["pickup_zone_id"],
        drop_address=order_in.drop_address,
        drop_pincode=order_in.drop_pincode,
        drop_zone_id=pricing["drop_zone_id"],
        length_cm=order_in.length_cm,
        width_cm=order_in.width_cm,
        height_cm=order_in.height_cm,
        actual_weight_kg=order_in.actual_weight_kg,
        volumetric_weight_kg=pricing["volumetric_weight_kg"],
        billable_weight_kg=pricing["billable_weight_kg"],
        order_type=pricing["order_type"],
        payment_type=pricing["payment_type"],
        base_charge=pricing["base_charge"],
        weight_charge=pricing["weight_charge"],
        cod_surcharge=pricing["cod_surcharge"],
        total_charge=pricing["total_charge"],
        status=OrderStatus.CREATED
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    # Log Created Event
    actor_label = "ADMIN" if current_user.role == UserRole.ADMIN else "CUSTOMER"
    creator_name = current_user.name
    history = OrderTrackingHistory(
        order_id=order.id,
        status=OrderStatus.CREATED,
        actor_id=current_user.id,
        actor_name=creator_name,
        actor_role=actor_label,
        notes=f"Order created. Auto-calculated charge: ₹{order.total_charge:.2f} (Billable Weight: {order.billable_weight_kg}kg)."
    )
    db.add(history)
    db.commit()

    # Attempt Auto Assignment immediately
    auto_assign_agent_to_order(db, order, actor_id=current_user.id if current_user.role == UserRole.ADMIN else None, actor_name="Auto Assigner")

    db.refresh(order)
    notify_order_status_change(db, order, previous_status="NONE", new_status=OrderStatus.CREATED)
    return format_order_response(order)

@router.get("", response_model=List[OrderOut])
def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    zone_filter: Optional[int] = Query(None, alias="zone_id"),
    agent_filter: Optional[int] = Query(None, alias="agent_id"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Order)

    # Role-based restriction
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Order.customer_id == current_user.id)
    elif current_user.role == UserRole.AGENT:
        query = query.filter(Order.agent_id == current_user.id)
    # Admin gets all orders by default

    # Admin Filter Options
    if status_filter:
        query = query.filter(Order.status == status_filter.upper())
    if zone_filter:
        query = query.filter((Order.pickup_zone_id == zone_filter) | (Order.drop_zone_id == zone_filter))
    if agent_filter:
        query = query.filter(Order.agent_id == agent_filter)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (Order.tracking_number.ilike(s)) |
            (Order.pickup_address.ilike(s)) |
            (Order.drop_address.ilike(s))
        )

    orders = query.order_by(Order.created_at.desc()).all()
    return [format_order_response(o) for o in orders]

@router.get("/notifications/logs", response_model=List[NotificationLogOut])
def list_notification_logs(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    return db.query(NotificationLog).order_by(NotificationLog.sent_at.desc()).limit(100).all()

@router.get("/{identifier}", response_model=OrderOut)
def get_order_detail(
    identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Order)
    if identifier.isdigit():
        order = query.filter(Order.id == int(identifier)).first()
    else:
        order = query.filter(Order.tracking_number == identifier.upper()).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden access to this order.")

    return format_order_response(order)

@router.put("/{order_id}/status", response_model=OrderOut)
def update_order_status_by_agent(
    order_id: int,
    update_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.AGENT, UserRole.ADMIN]))
):
    """
    Agent updates order status:
    PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED.
    Requires failure_reason if status is FAILED.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    if current_user.role == UserRole.AGENT and order.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the assigned agent for this order.")

    new_st = update_in.status.upper()
    if new_st not in [OrderStatus.PICKED_UP, OrderStatus.IN_TRANSIT, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED, OrderStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Invalid status transition for delivery agent.")

    if new_st == OrderStatus.FAILED and not update_in.failure_reason:
        raise HTTPException(status_code=400, detail="Failure reason is mandatory when flagging delivery as FAILED.")

    old_st = order.status
    order.status = new_st
    if update_in.failure_reason:
        order.failure_reason = update_in.failure_reason

    # If completed or failed, reduce workload
    if new_st in [OrderStatus.DELIVERED, OrderStatus.FAILED] and order.agent_id:
        prof = db.query(AgentProfile).filter(AgentProfile.user_id == order.agent_id).first()
        if prof and prof.current_workload > 0:
            prof.current_workload -= 1

    # Record immutable tracking history
    history = OrderTrackingHistory(
        order_id=order.id,
        status=new_st,
        actor_id=current_user.id,
        actor_name=current_user.name,
        actor_role=current_user.role,
        notes=update_in.notes or (f"Reason: {update_in.failure_reason}" if update_in.failure_reason else f"Status updated to {new_st}"),
        location_lat=update_in.location_lat,
        location_lng=update_in.location_lng
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    notify_order_status_change(db, order, previous_status=old_st, new_status=new_st, custom_notes=update_in.failure_reason or update_in.notes or "")
    return format_order_response(order)

@router.post("/{order_id}/reschedule", response_model=OrderOut)
def reschedule_failed_order(
    order_id: int,
    req: OrderRescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Failed delivery reschedule flow:
    - Customer receives notification of failed delivery.
    - Customer requests new target date and slot.
    - System updates status to RESCHEDULED.
    - System automatically triggers agent auto-reassignment for the new attempt!
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden.")

    if order.status != OrderStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only orders in FAILED status can be rescheduled.")

    old_st = order.status
    order.status = OrderStatus.RESCHEDULED
    order.rescheduled_date = req.rescheduled_date

    # Record history
    history = OrderTrackingHistory(
        order_id=order.id,
        status=OrderStatus.RESCHEDULED,
        actor_id=current_user.id,
        actor_name=current_user.name,
        actor_role=current_user.role,
        notes=f"Customer rescheduled delivery attempt for {req.rescheduled_date}. Notes: {req.notes or 'None'}"
    )
    db.add(history)
    db.commit()

    # Re-trigger Auto Assignment for rescheduled delivery
    reassigned_agent = auto_assign_agent_to_order(db, order, actor_id=current_user.id, actor_name="Reschedule Auto-Assigner")

    db.refresh(order)
    reassign_note = f"Rescheduled for {req.rescheduled_date}."
    if reassigned_agent:
        reassign_note += f" Reassigned to Agent {reassigned_agent.name}."

    notify_order_status_change(db, order, previous_status=old_st, new_status=order.status, custom_notes=reassign_note)
    return format_order_response(order)

@router.put("/{order_id}/override", response_model=OrderOut)
def admin_override_status(
    order_id: int,
    new_status: str = Query(...),
    notes: Optional[str] = Query("Admin manual status override"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Admin can override any order status at any point in the delivery lifecycle.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    new_st = new_status.upper()
    old_st = order.status
    order.status = new_st

    history = OrderTrackingHistory(
        order_id=order.id,
        status=new_st,
        actor_id=current_user.id,
        actor_name=current_user.name,
        actor_role="ADMIN",
        notes=f"Admin Manual Override: {notes}"
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    notify_order_status_change(db, order, previous_status=old_st, new_status=new_st, custom_notes=f"Status manually overridden by Admin. Reason: {notes}")
    return format_order_response(order)
