import asyncio

from app.core.database import SessionLocal
from app.services.ministry_service import MinistryService


async def run_sync():
    db = SessionLocal()
    try:
        service = MinistryService(db)
        return await service.sync_firms()
    finally:
        db.close()


if __name__ == "__main__":
    print(asyncio.run(run_sync()))
