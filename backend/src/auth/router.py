from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import schemas, service, dependencies
from src.database import get_db

router = APIRouter()


@router.post(
    "/signup",
    response_model=schemas.UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(
    db: Annotated[AsyncSession, Depends(get_db)], user_in: schemas.UserCreate
):
    db_user = await service.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    return await service.create_user(db, user_in)


@router.post(
    "/login", response_model=schemas.Token, summary="Get access token via password"
)
async def login(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = await service.get_user_by_email(db, email=form_data.username)
    if not user or not service.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = service.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserRead, summary="Get current user details")
async def read_users_me(
    current_user: Annotated[schemas.UserRead, Depends(dependencies.get_current_user)],
):
    return current_user
