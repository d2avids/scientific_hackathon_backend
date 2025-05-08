import datetime as dt

from sqlalchemy import select, delete

from auth.models import ResetCode


class ResetCodeRepository:
    def __init__(self, db):
        self._db = db

    async def get(self, user_id: int) -> ResetCode:
        result = await self._db.execute(
            select(ResetCode).where(ResetCode.user_id == user_id)  # type: ignore
        )
        return result.scalar()

    async def insert(self, code: str, user_id: int, expiration: dt.datetime) -> ResetCode:
        reset_code = ResetCode(code=code, user_id=user_id, expiration=expiration)
        self._db.add(reset_code)
        await self._db.commit()
        return reset_code

    async def delete(self, reset_code_id: int):
        await self._db.execute(delete(ResetCode).where(ResetCode.id == reset_code_id))  # type: ignore
        await self._db.commit()
