from typing import Optional, Sequence, Literal, Tuple

from exceptions import NotFoundError
from sqlalchemy import func, select, delete, or_, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from users.models import User, Participant, Mentor, UserDocument, Region
from users.schemas import UserCreate, ParticipantCreate, MentorCreate


class UserRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_all(
            self,
            search: Optional[str] = None,
            is_mentor: Optional[bool] = None,
            order_column: str = 'id',
            order_direction: Literal['ASC', 'DESC'] = 'ASC',
            offset: int = 0,
            limit: int = 10,
    ) -> Tuple[list[User], int]:
        base_query = select(User)

        filters = []
        if search:
            filters.append(
                or_(
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        if is_mentor is not None:
            filters.append(User.is_mentor == is_mentor)

        if filters:
            base_query = base_query.where(*filters)

        count_query = select(func.count(User.id))
        if filters:
            count_query = count_query.where(*filters)

        count_result = await self._db.execute(count_query)
        total = count_result.scalar() or 0

        column = getattr(User, order_column, None)
        if column is not None:
            if order_direction == 'ASC':
                base_query = base_query.order_by(asc(column))
            else:
                base_query = base_query.order_by(desc(column))

        base_query = base_query.options(
            joinedload(User.mentor),
            joinedload(User.participant)
        ).offset(offset).limit(limit)

        result = await self._db.execute(base_query)
        users_list = result.scalars().all()

        return users_list, total

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self._db.execute(
            select(User).where(User.id == user_id).options(  # type: ignore
                joinedload(User.mentor),
                joinedload(User.participant)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._db.execute(
            select(User).where(User.email == email).options(  # type: ignore
                joinedload(User.mentor),
                joinedload(User.participant)
            )
        )
        return result.scalar_one_or_none()

    async def create_user_and_mentor(
            self,
            user_data: UserCreate,
            mentor_data: MentorCreate
    ) -> tuple[User, Mentor]:
        async with self._db.begin():
            user = await self._create_user(user_data)
            mentor_data = mentor_data.model_dump()
            mentor_data.update({'user_id': user.id})
            mentor = await self._create_mentor(mentor_data)
        return user, mentor

    async def create_user_and_participant(
            self,
            user_data: UserCreate,
            participant_data: ParticipantCreate
    ) -> tuple[User, Participant]:
        async with self._db.begin():
            user = await self._create_user(user_data)
            participant_data = participant_data.model_dump()
            participant_data.update(({'user_id': user.id}))
            participant = await self._create_participant(participant_data)
        return user, participant

    async def _create_user(self, data: UserCreate) -> User:
        """Method to be used inside a transaction block. No commit applied"""
        user = User(**data.model_dump())
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user, attribute_names=['participant', 'mentor'])
        return user

    async def _create_participant(self, data: dict) -> Participant:
        """Method to be used inside a transaction block. No commit applied"""
        participant = Participant(**data)
        self._db.add(participant)
        await self._db.flush()
        await self._db.refresh(participant)
        return participant

    async def _create_mentor(self, data: dict) -> Mentor:
        """Method to be used inside a transaction block. No commit applied"""
        mentor = Mentor(**data)
        self._db.add(mentor)
        await self._db.flush()
        await self._db.refresh(mentor)
        return mentor

    async def update_user(self, user_id: int, update_data: dict) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError('User not found')
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def update_participant(self, user_id: int, update_data: dict) -> Participant:
        result = await self._db.execute(
            select(Participant).where(Participant.user_id == user_id)  # type: ignore
        )
        participant = result.scalar_one_or_none()
        if not participant:
            raise NotFoundError('Participant not found')
        for key, value in update_data.items():
            if hasattr(participant, key):
                setattr(participant, key, value)
        await self._db.commit()
        await self._db.refresh(participant)
        return participant

    async def update_mentor(self, user_id: int, update_data: dict) -> Mentor:
        result = await self._db.execute(
            select(Mentor).where(Mentor.user_id == user_id)  # type: ignore
        )
        mentor = result.scalar_one_or_none()
        if not mentor:
            raise NotFoundError('Mentor not found')
        for key, value in update_data.items():
            if hasattr(mentor, key):
                setattr(mentor, key, value)
        await self._db.commit()
        await self._db.refresh(mentor)
        return mentor

    async def verify(self, user: User) -> None:
        user.verified = True
        await self._db.commit()
        await self._db.refresh(user)

    async def delete(self, user: User) -> None:
        await self._db.execute(delete(User).where(User.id == user.id))  # type: ignore
        await self._db.commit()


class UserDocumentRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, document_id: int) -> Optional[UserDocument]:
        result = await self._db.execute(select(UserDocument).where(UserDocument.id == document_id))  # type: ignore
        return result.scalar_one_or_none()

    async def get_user_documents(self, user_id: int) -> Sequence[UserDocument]:
        result = await self._db.execute(
            select(UserDocument).where(UserDocument.user_id == user_id)  # type: ignore
        )
        return result.scalars().all()

    async def create(
            self,
            user_id: int,
            name: str,
            path: str,
            size: float,
            mimetype: str,
    ) -> UserDocument:
        document = UserDocument(
            user_id=user_id,
            name=name,
            path=path,
            size=size,
            mimetype=mimetype,
        )
        self._db.add(document)
        await self._db.commit()
        await self._db.refresh(document)
        return document

    async def delete(self, document_id: int) -> None:
        await self._db.execute(
            delete(UserDocument).where(UserDocument.id == document_id)  # type: ignore
        )
        await self._db.commit()


class RegionRepo:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_all(self, search: str, name: str, code: int) -> Sequence[Region]:
        query = select(Region)
        if search:
            query = query.where(Region.name.ilike(f'%{search}%'))
        if name:
            query = query.where(Region.name == name)  # type: ignore
        if code:
            query = query.where(Region.code == code)  # type: ignore
        query = query.order_by(Region.name)
        result = await self._db.execute(query)
        return result.scalars().all()
