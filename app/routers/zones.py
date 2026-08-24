from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Zone, AreaMapping, UserRole
from app.schemas import ZoneCreate, ZoneOut, AreaMappingCreate, AreaMappingOut
from app.routers.auth import require_roles

router = APIRouter(prefix="/api/zones", tags=["Zones & Area Management"])

@router.get("", response_model=List[ZoneOut])
def list_zones(db: Session = Depends(get_db)):
    return db.query(Zone).all()

@router.post("", response_model=ZoneOut)
def create_zone(
    zone_in: ZoneCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    existing = db.query(Zone).filter(Zone.code == zone_in.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Zone with code '{zone_in.code}' already exists.")

    zone = Zone(
        name=zone_in.name,
        code=zone_in.code.upper(),
        description=zone_in.description
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone

@router.put("/{zone_id}", response_model=ZoneOut)
def update_zone(
    zone_id: int,
    zone_in: ZoneCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found.")

    zone.name = zone_in.name
    zone.code = zone_in.code.upper()
    zone.description = zone_in.description
    db.commit()
    db.refresh(zone)
    return zone

@router.delete("/{zone_id}")
def delete_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found.")

    db.delete(zone)
    db.commit()
    return {"message": "Zone deleted successfully"}

@router.post("/{zone_id}/areas", response_model=AreaMappingOut)
def add_area_to_zone(
    zone_id: int,
    area_in: AreaMappingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found.")

    area = AreaMapping(
        zone_id=zone_id,
        pincode=area_in.pincode.strip(),
        area_name=area_in.area_name.strip(),
        city=area_in.city.strip()
    )
    db.add(area)
    db.commit()
    db.refresh(area)
    return area

@router.delete("/areas/{area_id}")
def remove_area(
    area_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles([UserRole.ADMIN]))
):
    area = db.query(AreaMapping).filter(AreaMapping.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area mapping not found.")

    db.delete(area)
    db.commit()
    return {"message": "Area mapping deleted successfully"}
