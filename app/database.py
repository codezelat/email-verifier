from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    status: Mapped[str] = mapped_column(String(32))
    sub_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[int] = mapped_column()
    processing_time_ms: Mapped[int] = mapped_column()
    from_cache: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    checks_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<VerificationLog {self.email} -> {self.status}>"


engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None
database_enabled = False


async def init_database() -> None:
    global engine, async_session_factory, database_enabled

    db_url = settings.database_url_effective

    try:
        connect_args = {}
        if settings.is_sqlite:
            connect_args["check_same_thread"] = False

        engine = create_async_engine(
            db_url,
            echo=settings.debug,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        database_enabled = True
        logger.info("database_initialized", url=db_url.split("@")[-1] if "@" in db_url else db_url)

    except Exception as e:
        logger.warning("database_init_failed", error=str(e))
        database_enabled = False


async def close_database() -> None:
    global engine, async_session_factory, database_enabled
    if engine:
        await engine.dispose()
        engine = None
        async_session_factory = None
        database_enabled = False
        logger.info("database_closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if not database_enabled or async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def log_verification(
    request_id: str,
    email: str,
    status: str,
    sub_status: str | None,
    confidence_score: int,
    processing_time_ms: int,
    from_cache: bool,
    checks_json: str | None,
) -> None:
    if not database_enabled or async_session_factory is None:
        return
    try:
        async with async_session_factory() as session:
            log_entry = VerificationLog(
                request_id=request_id,
                email=email,
                status=status,
                sub_status=sub_status,
                confidence_score=confidence_score,
                processing_time_ms=processing_time_ms,
                from_cache=from_cache,
                checks_json=checks_json,
            )
            session.add(log_entry)
            await session.commit()
    except Exception as e:
        logger.warning("log_verification_failed", error=str(e), email=email)
