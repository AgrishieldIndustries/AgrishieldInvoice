import ssl
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Build connect_args - add SSL for Supabase/PostgreSQL connections
connect_args = {}
db_url = settings.async_database_url

if "supabase.co" in db_url or ("postgresql+asyncpg" in db_url and "sqlite" not in db_url):
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_ctx

# Create async engine
engine = create_async_engine(
    db_url,
    pool_pre_ping=True,
    echo=False,
    connect_args=connect_args,
)

# Async session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Declarative base
class Base(DeclarativeBase):
    pass

# Dependency for DB Session
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
