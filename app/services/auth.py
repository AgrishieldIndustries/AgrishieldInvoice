from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.user import user_repo
from app.core import security
from app.models.user import User
from app.schemas.user import UserCreate, Token

class AuthService:
    @staticmethod
    async def authenticate(
        db: AsyncSession, *, email: str, password: str
    ) -> Optional[User]:
        user = await user_repo.get_by_email(db, email=email)
        if not user:
            return None
        if not security.verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def login_user(db: AsyncSession, *, email: str, password: str) -> Token:
        user = await AuthService.authenticate(db, email=email, password=password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account",
            )
        
        access_token = security.create_access_token(subject=str(user.id))
        return Token(
            access_token=access_token,
            token_type="bearer",
            role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            name=user.full_name,
        )

    @staticmethod
    async def register_user(db: AsyncSession, *, user_in: UserCreate) -> User:
        existing = await user_repo.get_by_email(db, email=user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )
            
        hashed_password = security.get_password_hash(user_in.password)
        db_obj = User(
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            role=user_in.role,
            is_active=user_in.is_active,
        )
        db.add(db_obj)
        await db.flush()
        return db_obj
