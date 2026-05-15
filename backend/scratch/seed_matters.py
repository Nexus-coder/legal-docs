import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.auth.service import get_user_by_email
from src.matters.service import create_matter
from src.matters.schemas import MatterCreate
from src.models import Base
from src.config import settings

async def seed():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionFactory() as db:
        user = await get_user_by_email(db, "success_user@test.com")
        if not user:
            print("User not found. Please sign up first.")
            return
        
        uid = user.id
            
        # Add some matters
        matters = [
            MatterCreate(
                case_number="ELC/E045/2024",
                division="Environment & Land Court",
                status="Drafting",
                verification_done=4,
                verification_total=12,
                last_activity="Retrieved Giella v. Cassman (1973)"
            ),
            MatterCreate(
                case_number="CIV/102/2023",
                division="Civil Division",
                status="Verified",
                verification_done=15,
                verification_total=15,
                last_activity="Verified precedent: Smith v. Jones"
            )
        ]
        
        for m in matters:
            await create_matter(db, user_id=uid, matter_in=m)
            print(f"Created matter: {m.case_number}")

if __name__ == "__main__":
    asyncio.run(seed())
