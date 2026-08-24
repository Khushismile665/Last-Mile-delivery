import math
from sqlalchemy.orm import Session
from app.models import Zone, AreaMapping, RateCard, CODSurcharge
from fastapi import HTTPException

def resolve_zone(db: Session, pincode: str, address: str = "") -> Zone:
    """
    Detect zone based on pincode or area name in address.
    Falls back to default first zone if no exact match found.
    """
    pincode = pincode.strip() if pincode else ""
    
    # 1. Exact pincode match
    if pincode:
        area_match = db.query(AreaMapping).filter(AreaMapping.pincode == pincode).first()
        if area_match and area_match.zone:
            return area_match.zone
            
    # 2. Match area name inside address string
    if address:
        all_areas = db.query(AreaMapping).all()
        for area in all_areas:
            if area.area_name.lower() in address.lower() or area.pincode in address:
                return area.zone

    # 3. Pincode prefix fallback (e.g. 11xxxx -> North Zone, 40xxxx -> West Zone, etc.)
    if len(pincode) >= 2:
        prefix = pincode[:2]
        zone = db.query(Zone).filter(Zone.code.ilike(f"%{prefix}%") | Zone.name.ilike(f"%{prefix}%")).first()
        if zone:
            return zone

    # 4. Fallback to default zone
    default_zone = db.query(Zone).first()
    if not default_zone:
        # Create fallback zone if none exists
        default_zone = Zone(name="Central Zone", code="CENTRAL-01", description="Default Fallback Zone")
        db.add(default_zone)
        db.commit()
        db.refresh(default_zone)
    return default_zone

def calculate_volumetric_weight(length_cm: float, width_cm: float, height_cm: float) -> float:
    """
    Standard logistics formula: (L x B x H) / 5000
    Returns volumetric weight in kg rounded to 2 decimal places.
    """
    vol_weight = (length_cm * width_cm * height_cm) / 5000.0
    return round(vol_weight, 2)

def calculate_order_price(
    db: Session,
    pickup_pincode: str,
    pickup_address: str,
    drop_pincode: str,
    drop_address: str,
    length_cm: float,
    width_cm: float,
    height_cm: float,
    actual_weight_kg: float,
    order_type: str,
    payment_type: str
) -> dict:
    """
    Dynamic rate calculation engine:
    1. Volumetric weight = (L x B x H) / 5000
    2. Billable weight = max(actual, volumetric)
    3. Detect pickup and drop zones
    4. Route type = INTRA if pickup_zone == drop_zone else INTER
    5. Fetch admin-configured RateCard for (order_type, route_type)
    6. Fetch admin-configured CODSurcharge for order_type if COD
    7. Calculate charges and return itemized breakdown
    """
    order_type = order_type.upper().strip()
    payment_type = payment_type.upper().strip()
    
    if order_type not in ["B2B", "B2C"]:
        raise HTTPException(status_code=400, detail="Invalid order_type. Must be B2B or B2C.")
        
    if payment_type not in ["PREPAID", "COD"]:
        raise HTTPException(status_code=400, detail="Invalid payment_type. Must be PREPAID or COD.")

    # 1. Volumetric & Billable Weight
    volumetric_weight = calculate_volumetric_weight(length_cm, width_cm, height_cm)
    billable_weight = max(actual_weight_kg, volumetric_weight)
    billable_weight = round(billable_weight, 2)

    # 2. Zone Detection
    pickup_zone = resolve_zone(db, pickup_pincode, pickup_address)
    drop_zone = resolve_zone(db, drop_pincode, drop_address)

    # 3. Route Classification
    route_type = "INTRA" if pickup_zone.id == drop_zone.id else "INTER"

    # 4. Rate Card Lookup
    rate_card = db.query(RateCard).filter(
        RateCard.order_type == order_type,
        RateCard.route_type == route_type
    ).first()

    if not rate_card:
        # Default dynamic fallback if admin hasn't seeded yet
        base = 100.0 if order_type == "B2B" else 50.0
        per_kg = 20.0 if route_type == "INTER" else 10.0
        min_chg = 120.0 if order_type == "B2B" else 60.0
        rate_card = RateCard(
            order_type=order_type,
            route_type=route_type,
            base_rate=base,
            per_kg_rate=per_kg,
            min_charge=min_chg
        )
        db.add(rate_card)
        db.commit()
        db.refresh(rate_card)

    # Base charge and weight charge
    base_charge = round(rate_card.base_rate, 2)
    weight_charge = round(billable_weight * rate_card.per_kg_rate, 2)
    subtotal = base_charge + weight_charge
    
    # Enforce minimum charge floor
    subtotal = max(subtotal, rate_card.min_charge)
    subtotal = round(subtotal, 2)

    # 5. COD Surcharge Calculation
    cod_surcharge = 0.0
    if payment_type == "COD":
        cod_config = db.query(CODSurcharge).filter(CODSurcharge.order_type == order_type).first()
        if not cod_config:
            cod_config = CODSurcharge(order_type=order_type, fixed_fee=25.0, percentage_fee=2.0)
            db.add(cod_config)
            db.commit()
            db.refresh(cod_config)
            
        fixed = cod_config.fixed_fee
        percent = (subtotal * cod_config.percentage_fee) / 100.0
        cod_surcharge = round(fixed + percent, 2)

    total_charge = round(subtotal + cod_surcharge, 2)

    return {
        "volumetric_weight_kg": volumetric_weight,
        "actual_weight_kg": actual_weight_kg,
        "billable_weight_kg": billable_weight,
        "pickup_zone_id": pickup_zone.id,
        "pickup_zone_name": pickup_zone.name,
        "pickup_zone_code": pickup_zone.code,
        "drop_zone_id": drop_zone.id,
        "drop_zone_name": drop_zone.name,
        "drop_zone_code": drop_zone.code,
        "route_type": route_type,
        "order_type": order_type,
        "payment_type": payment_type,
        "base_charge": base_charge,
        "weight_charge": weight_charge,
        "cod_surcharge": cod_surcharge,
        "total_charge": total_charge,
        "rate_card_details": {
            "rate_card_id": rate_card.id,
            "base_rate": rate_card.base_rate,
            "per_kg_rate": rate_card.per_kg_rate,
            "min_charge": rate_card.min_charge
        }
    }
