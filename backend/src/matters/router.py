from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.auth.dependencies import get_current_user
from src.auth.schemas import UserRead
from src.matters import schemas, service

router = APIRouter()


@router.get("/", response_model=List[schemas.MatterRead])
async def list_matters(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    return await service.get_user_matters(db, user_id=current_user.id)


@router.post("/", response_model=schemas.MatterRead, status_code=status.HTTP_201_CREATED)
async def create_matter(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
    matter_in: schemas.MatterCreate,
):
    return await service.create_matter(db, user_id=current_user.id, matter_in=matter_in)
