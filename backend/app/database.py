from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()
database_url = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg://"
)

engine = create_engine(
    database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
)


def get_db_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
