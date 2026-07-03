from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.user import UserOut, UserCreate, Token
from app.services.auth import AuthService

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # Delegate authentication and token packaging business logic to AuthService
    token = await AuthService.login_user(
        db, email=form_data.username, password=form_data.password
    )
    return token

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Delegate registration verification to AuthService
    user = await AuthService.register_user(db, user_in=user_in)
    return user

@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    return current_user
