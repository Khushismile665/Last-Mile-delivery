from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import RateCard, CODSurcharge, UserRole
from app.schemas import (
    RateCardCreate, RateCardOut,
    CODSurchargeCreate, CODSurchargeOut,
    PriceEstimateRequest, PriceEstimateResponse
)
from app.rate_engine import calculate_order_price
from app.routers.auth import require_roles

router = APIRouter(prefix="/api/rates", tags=["Rate Engine & Configuration"])

@router.post("/calculate", response_model=PriceEstimateResponse)
def estimate_order_price(req: PriceEstimateRequest, db: Session = Depends(get_db)):
    """
    Public Endpoint: Calculates volumetric weight, billable weight, zone detection,
    rate card selection, and COD surcharge before customer confirms order.
    """
    return calculate_order_price(
        db=db,
        pickup_pincode=req.pickup_pincode,
        pickup_address=req.pickup_address or "",
        drop_pincode=req.drop_pincode,
        drop_address=req.drop_address or "",
        length_cm=req.length_cm,
        width_cm=req.width_cm,
        height_cm=req.height_cm,
        actual_weight_kg=req.actual_weight_kg,
        order_type=req.order_type,
        payment_type=req.payment_type
    )

@router.get("/cards", response_model=List[RateCardOut])
def list_rate_cards(db: Session = Depends(get_db)):
    return db.query(RateCard).all()

@router.post("/cards", response_model=RateCardOut)
def upsert_rate_card(
    card_in: RateCardCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    order_type = card_in.order_type.upper()
    route_type = card_in.route_type.upper()

    card = db.query(RateCard).filter(
        RateCard.order_type == order_type,
        RateCard.route_type == route_type
    ).first()

    if card:
        card.base_rate = card_in.base_rate
        card.per_kg_rate = card_in.per_kg_rate
        card.min_charge = card_in.min_charge
    else:
        card = RateCard(
            order_type=order_type,
            route_type=route_type,
            base_rate=card_in.base_rate,
            per_kg_rate=card_in.per_kg_rate,
            min_charge=card_in.min_charge
        )
        db.add(card)

    db.commit()
    db.refresh(card)
    return card

@router.get("/cod", response_model=List[CODSurchargeOut])
def list_cod_surcharges(db: Session = Depends(get_db)):
    return db.query(CODSurcharge).all()

@router.post("/cod", response_model=CODSurchargeOut)
def upsert_cod_surcharge(
    cod_in: CODSurchargeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    order_type = cod_in.order_type.upper()
    cod = db.query(CODSurcharge).filter(CODSurcharge.order_type == order_type).first()

    if cod:
        cod.fixed_fee = cod_in.fixed_fee
        cod.percentage_fee = cod_in.percentage_fee
    else:
        cod = CODSurcharge(
            order_type=order_type,
            fixed_fee=cod_in.fixed_fee,
            percentage_fee=cod_in.percentage_fee
        )
        db.add(cod)

    db.commit()
    db.refresh(cod)
    return cod
