import datetime as dt

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from settings import settings


class Base(DeclarativeBase):
    __abstract__ = True


class CreatedUpdatedAt(Base):
    __abstract__ = True

    created_at: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=dt.datetime.now(dt.UTC)
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=dt.datetime.now(dt.UTC),
        onupdate=dt.datetime.now(dt.UTC)
    )


engine = create_async_engine(
    url=settings.DATABASE_DSN,
    echo=settings.DEBUG,
)

async_session = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession,
)


async def get_db_session() -> AsyncSession:
    async with async_session() as session_:
        yield session_
