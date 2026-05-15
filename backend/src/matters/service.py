from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.matters.models import Matter
from src.matters.schemas import MatterCreate


async def get_user_matters(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Matter).where(Matter.user_id == user_id).order_by(Matter.updated_at.desc())
    )
    return result.scalars().all()


async def create_matter(db: AsyncSession, user_id: int, matter_in: MatterCreate):
    db_matter = Matter(
        user_id=user_id,
        **matter_in.model_dump()
    )
    db.add(db_matter)
    await db.commit()
    await db.refresh(db_matter)
    return db_matter


async def get_user_dashboard_stats(db: AsyncSession, user_id: int):
    # This is a simplified version of stats
    # In a real app, citations_verified might come from another table
    
    matters = await get_user_matters(db, user_id)
    
    citations_current = sum(m.verification_done for m in matters)
    citations_total = sum(m.verification_total for m in matters)
    
    draft_status = {
        "drafting": len([m for m in matters if m.status == "Drafting"]),
        "verified": len([m for m in matters if m.status == "Verified"]),
        "exported": len([m for m in matters if m.status == "Exported"]),
    }
    
    return {
        "citations_verified": {"current": citations_current, "total": citations_total},
        "recent_matches": 0, # Placeholder for now
        "draft_status": draft_status,
    }
