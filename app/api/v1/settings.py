from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.company_settings import CompanySettings
from app.schemas.company_settings import CompanySettingsOut, CompanySettingsUpdate

router = APIRouter()

@router.get("/", response_model=CompanySettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(CompanySettings).where(CompanySettings.id == 1))
    settings = result.scalars().first()
    if not settings:
        # Auto-create default settings if none exist
        settings = CompanySettings()
        db.add(settings)
        await db.flush()
    return settings

@router.put("/", response_model=CompanySettingsOut)
async def update_settings(
    settings_in: CompanySettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Only Admin can update settings
    if current_user.role.value != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin users can update company settings."
        )

    result = await db.execute(select(CompanySettings).where(CompanySettings.id == 1))
    settings = result.scalars().first()
    if not settings:
        settings = CompanySettings()
        db.add(settings)
        await db.flush()

    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    await db.flush()
    return settings
