from app.models import Acknowledgement
from .base import CRUDBase
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

class CRUDAcknowledgement(CRUDBase):
    
    async def create_acknowledgement(self, responder_id: UUID, delivery_id: UUID, message: str | None, db: AsyncSession) -> Acknowledgement:
        new_ack = Acknowledgement(
            responder_id=responder_id,
            delivery_id=delivery_id,
            message=message
        )
        db.add(new_ack)
        await db.commit()
        await db.refresh(new_ack)
        return new_ack

acknowledgement_crud = CRUDAcknowledgement(Acknowledgement)