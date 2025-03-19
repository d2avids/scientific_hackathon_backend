import json
from math import ceil
from typing import Optional, Tuple

from auth.config import PasswordEncryption
from fastapi import status, HTTPException, UploadFile, BackgroundTasks
from pydantic_core import ValidationError
from settings import settings
from sqlalchemy.exc import IntegrityError
from users.models import User, UserDocument
from users.repositories import UserRepo, UserDocumentRepo, RegionRepo
from users.schemas import UserCreate, UserInDB, MentorInDB, ParticipantInDB, UserDocumentInDB, UserUpdate, RegionInDB
from utils import clean_errors, parse_ordering, create_field_map_for_model, FileService, send_mail


class UserService:
    field_map: dict = create_field_map_for_model(UserInDB)

    def __init__(self, repo: UserRepo):
        self._repo = repo

    async def get_all(
            self,
            search: str = None,
            is_mentor: bool = None,
            ordering: str = None,
            offset: int = 0,
            limit: int = 10,
    ) -> Tuple[list[UserInDB], int, int]:
        """Returns tuple: (list of pydantic models, total, total_pages)."""
        order_column, order_direction = parse_ordering(ordering, field_map=self.field_map)

        entities, total = await self._repo.get_all(
            search=search,
            is_mentor=is_mentor,
            order_column=order_column,
            order_direction=order_direction,
            offset=offset,
            limit=limit
        )

        users_in_db = [UserInDB.model_validate(u) for u in entities]

        total_pages = ceil(total / limit) if total > 0 else 1

        return users_in_db, total, total_pages

    async def get_by_id(self, user_id: int) -> UserInDB:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found.'
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
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User with this email already exists OR region_id does not exist.'
            )

    async def update(
            self,
            user_id: int,
            update_data: Optional[str],
            current_user: User,
            photo: UploadFile = None,
    ) -> UserInDB:
        if update_data:
            try:
                data_dict = json.loads(update_data)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Invalid JSON in user_data field.'
                )

            try:
                update_model = UserUpdate(**data_dict)
            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=clean_errors(e.errors())
                )
            except TypeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Data string must be a valid JSON.'
                )

            update_data: dict = update_model.model_dump(exclude_unset=True)
        else:
            update_data: dict = {}

        if photo == '':
            if current_user.photo_path:
                old_user_photo_full_path = await FileService.construct_full_path_from_relative_path(
                    current_user.photo_path
                )
                await FileService.delete_file_from_fs(old_user_photo_full_path)
                update_data['photo_path'] = None

        if photo:
            result = await FileService.upload_file(
                file=photo,
                path_segments=['photos', str(user_id)],
                allowed_mime_types=['image/jpeg', 'image/png', 'image/bmp'],
                size_limit_megabytes=10,
            )
            update_data['photo_path'] = result.relative_path

        main_fields = {}
        participant_data = None
        mentor_data = None

        if 'participant' in update_data:
            participant_data = update_data.pop('participant')
        if 'mentor' in update_data:
            mentor_data = update_data.pop('mentor')

        for key in (list(UserUpdate.__fields__.keys()) + ['photo_path']):  # type: ignore
            if key in update_data:
                main_fields[key] = update_data[key]

        if main_fields:
            current_user = await self._repo.update_user(user_id, main_fields)

        if participant_data and not current_user.is_mentor:
            try:
                current_user.participant = await self._repo.update_participant(user_id, participant_data)
            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Region does not exist.'
                )

        if mentor_data and current_user.is_mentor:
            current_user.mentor = await self._repo.update_mentor(user_id, mentor_data)

        return UserInDB.model_validate(current_user)

    async def verify(self, user_id: int, background_tasks: BackgroundTasks) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found.'
            )
        if user.verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User is already verified.'
            )
        await self._repo.verify(user)
        background_tasks.add_task(
            send_mail,
            to_email=user.email,
            subject='Верификация на сайте "Научный Хакатон" успешно пройдена.',
            message=f'Добрый день, {user.first_name}!\n\n'
                    f'Ваш аккаунт на сайте {settings.SERVER_URL} был верифицирован администратором.\n\n '
                    f'С уважением, команда сайта Научный Хакатон.'
        )  # type: ignore

    async def decline_registration(self, user_id: int, background_tasks: BackgroundTasks) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        if user.verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User is already verified'
            )
        await self._repo.delete(user)
        background_tasks.add_task(
            send_mail,
            to_email=user.email,
            subject='Верификация на сайте "Научный Хакатон" успешно пройдена.',
            message=f'Добрый день, {user.first_name}!\n\n'
                    f'Ваш аккаунт на сайте {settings.SERVER_URL} был верифицирован администратором.\n\n '
                    f'С уважением, команда сайта Научный Хакатон.'
        )  # type: ignore


class UserDocumentService:
    def __init__(self, repo: UserDocumentRepo):
        self._repo = repo

    async def get_by_id(self, document_id: int) -> UserDocumentInDB:
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
        existing_docs = await self.get_user_documents(user_id)
        docs_number = len(existing_docs)
        if docs_number >= 5:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Maximum amount of documents ({docs_number}) are already created for this user.'
            )

        result = await FileService.upload_file(
            file=uploaded_file,
            path_segments=['documents', str(user_id)],
            allowed_mime_types=[
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain',
            ],
            size_limit_megabytes=10,
        )

        document = await self._repo.create(
            user_id=user_id,
            path=result.relative_path,
            name=result.name,
            size=result.size_bytes,
            mimetype=result.mime_type,
        )
        return UserDocumentInDB.model_validate(document)

    async def delete(self, document_id: int, document: UserDocument) -> None:
        await self._repo.delete(document_id)
        full_path = await FileService.construct_full_path_from_relative_path(document.path)
        await FileService.delete_file_from_fs(full_path)


class RegionService:
    def __init__(self, repo: RegionRepo):
        self._repo = repo

    async def get_all(self, search: str, name: str, code: int) -> list[RegionInDB]:
        regions = await self._repo.get_all(search, name, code)
        return [RegionInDB.model_validate(region) for region in regions]
