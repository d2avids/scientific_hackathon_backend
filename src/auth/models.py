import datetime as dt

from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import TIMESTAMP

from database import Base


class ResetCode(Base):
    __tablename__ = 'reset_codes'

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    expiration: Mapped[dt.datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
