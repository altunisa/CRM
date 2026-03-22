from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ministry_service import MinistryService

router = APIRouter()


@router.post("/sync-firms")
async def sync_firms(id_or_tax_no: str, db: Session = Depends(get_db)):
    service = MinistryService(db)
    result = await service.sync_firms(id_or_tax_no=id_or_tax_no)
    return result
@router.post("/sync-dealers")
async def sync_dealers(db: Session = Depends(get_db)):
    service = MinistryService(db)
    return await service.sync_dealers()


@router.post("/sync-wholesalers")
async def sync_wholesalers(db: Session = Depends(get_db)):
    service = MinistryService(db)
    return await service.sync_wholesalers()


@router.post("/sync-licencees")
async def sync_licencees(db: Session = Depends(get_db)):
    service = MinistryService(db)
    return await service.sync_licencees()