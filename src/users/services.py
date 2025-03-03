import os
from typing import Optional, Sequence

import aiofiles
from auth.config import PasswordEncryption
from fastapi import status, HTTPException, UploadFile
from settings import settings, BASE_DIR
from sqlalchemy.exc import IntegrityError
from users.repositories import UserRepo, UserDocumentRepo, RegionRepo
from users.schemas import UserCreate, UserInDB, MentorInDB, ParticipantInDB, UserDocumentInDB, UserUpdate, RegionInDB
from utils import parse_ordering, create_field_map_for_model


class UserService:
    field_map: dict = create_field_map_for_model(UserInDB)

    def __init__(self, repo: UserRepo):
        self._repo = repo

    async def get_all(
        self,
        search: Optional[str] = None,
        is_mentor: Optional[bool] = None,
        ordering: str = None,
    ) -> Sequence[UserInDB]:
        order_column, order_direction = parse_ordering(ordering, self.field_map, default_field="id")

        users = await self._repo.get_all(
            search=search,
            is_mentor=is_mentor,
            order_column=order_column,
            order_direction=order_direction
        )
        return [UserInDB.model_validate(user) for user in users]

    async def get_by_id(self, user_id: int) -> UserInDB:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        return UserInDB.model_validate(user)

    async def get_by_email(self, email: str) -> UserInDB:
        user = await self._repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        return UserInDB.model_validate(user)

    async def create(self, user: UserCreate) -> UserInDB:
        try:
            participant_data, mentor_data = user.participant, user.mentor
            user = user.copy(exclude={'participant', 'mentor'})
            user.password = PasswordEncryption.hash_password(user.password)
            if user.is_mentor:
                user, mentor = await self._repo.create_user_and_mentor(user, mentor_data)
                user_model = UserInDB.model_validate(user)
                user_model.mentor = MentorInDB.model_validate(mentor)
            else:
                user, participant = await self._repo.create_user_and_participant(user, participant_data)
                user_model = UserInDB.model_validate(user)
                user_model.participant = ParticipantInDB.model_validate(participant)
            return user_model
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='User with this email already exists'
            ) from exc

    async def update(
        self,
        user_id: int,
        update_data: dict,
        photo: UploadFile = None
    ) -> UserInDB:
        """
        Выполняет частичное обновление (PATCH) пользователя:
          1. Если передан файл, сохраняем фото (и удаляем старое).
          2. Обновляем только переданные поля пользователя.
          3. Если есть данные для участника/ментора — обновляем их, исходя из is_mentor у пользователя.
        """
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )

        if photo is None:
            if user.photo_path:
                safe_photo_path = user.photo_path.lstrip("/\\")
                old_user_photo_full_path = BASE_DIR / safe_photo_path
                if old_user_photo_full_path.exists():
                    old_user_photo_full_path.unlink()
                update_data['photo_path'] = None

        if photo:
            # Validate file format
            allowed_types = ['image/jpeg', 'image/png', 'image/bmp']
            if photo.content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Invalid image format. Allowed formats: JPEG, PNG, BMP'
                )

            content = await photo.read()
            if len(content) > 5 * 1024 * 1024:  # 5 mb
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Image file size exceeds the limit of 5 MB'
                )
            await photo.seek(0)

            if user.photo_path:
                safe_photo_path = user.photo_path.lstrip('/\\')
                old_user_photo_full_path = BASE_DIR / safe_photo_path
                if old_user_photo_full_path.exists():
                    old_user_photo_full_path.unlink()

            photo_dir = settings.MEDIA_DIR / 'photos'
            photo_dir.mkdir(parents=True, exist_ok=True)

            user_dir = photo_dir / str(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)

            full_path = (user_dir / photo.filename).resolve()

            async with aiofiles.open(full_path, 'wb') as out_file:
                await out_file.write(content)

            relative_path = f'/media/photos/{user_id}/{photo.filename}'
            update_data['photo_path'] = relative_path

        main_fields = {}
        participant_data = None
        mentor_data = None
        for key in (list(UserUpdate.__fields__.keys()) + ['photo_path']):  # type: ignore
            if key in update_data:
                main_fields[key] = update_data[key]

        if 'participant' in update_data:
            participant_data = update_data['participant']
        if 'mentor' in update_data:
            mentor_data = update_data['mentor']

        if main_fields:
            user = await self._repo.update_user(user_id, main_fields)

        if participant_data and not user.is_mentor:
            user.participant = await self._repo.update_participant(user_id, participant_data)

        if mentor_data and user.is_mentor:
            user.mentor = await self._repo.update_mentor(user_id, mentor_data)

        return UserInDB.model_validate(user)

    async def verify(self, user_id: int) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        if user.verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='User is already verified'
            )
        await self._repo.verify(user)

    async def decline_registration(self, user_id: int) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        if user.verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='User is already verified'
            )
        await self._repo.delete(user)


class UserDocumentService:
    def __init__(self, repo: UserDocumentRepo):
        self._repo = repo

    async def get_by_id(self, document_id) -> UserDocumentInDB:
        document = await self._repo.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Document not found'
            )
        return UserDocumentInDB.model_validate(document)

    async def get_user_documents(self, user_id: int) -> list[UserDocumentInDB]:
        documents = await self._repo.get_user_documents(user_id)
        return [UserDocumentInDB.model_validate(document) for document in documents]

    async def create(
            self,
            user_id: int,
            uploaded_file: UploadFile,
    ) -> UserDocumentInDB:
        documents_dir = os.path.join(settings.MEDIA_DIR, 'documents')
        os.makedirs(documents_dir, exist_ok=True)
        user_dir = os.path.join(documents_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        full_path = os.path.abspath(os.path.join(user_dir, uploaded_file.filename))

        async with aiofiles.open(full_path, 'wb') as out_file:
            content = await uploaded_file.read()
            await out_file.write(content)

        size = len(content)
        mimetype = uploaded_file.content_type

        document = await self._repo.create(
            user_id=user_id,
            path=full_path,
            name=uploaded_file.filename,
            size=size,
            mimetype=mimetype,
        )
        return UserDocumentInDB.model_validate(document)

    async def delete(self, document_id) -> None:
        await self._repo.delete(document_id)


class RegionService:
    def __init__(self, repo: RegionRepo):
        self._repo = repo

    async def get_all(self, search: str, name: str, code: int) -> list[RegionInDB]:
        regions = await self._repo.get_all(search, name, code)
        return [RegionInDB.model_validate(region) for region in regions]
