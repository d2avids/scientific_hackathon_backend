import json
import os
from math import ceil
from typing import Optional, Sequence

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic_core import ValidationError
from sqlalchemy.exc import IntegrityError

from auth.config import PasswordEncryption
from constants import (REJECTED_REGISTRATION_EMAIL_MESSAGE,
                       REJECTED_REGISTRATION_EMAIL_SUBJECT,
                       SUCCESSFUL_REGISTRATION_EMAIL_MESSAGE,
                       SUCCESSFUL_REGISTRATION_EMAIL_SUBJECT)
from users.models import User, UserDocument
from users.repositories import RegionRepo, UserDocumentRepo, UserRepo
from users.schemas import (MentorInDB, ParticipantInDB, RegionInDB, UserCreate,
                           UserDocumentInDB, UserInDB, UserUpdate, UserInDBWithTeamID)
from utils import (FileService, clean_errors, create_field_map_for_model,
                   dict_to_text, parse_ordering, send_mail)


class UserService:
    field_map: dict = create_field_map_for_model(UserInDB)

    def __init__(self, repo: UserRepo):
        self._repo = repo

    async def get_all(
            self,
            search: Optional[str] = None,
            is_mentor: Optional[bool] = None,
            is_team_member: Optional[bool] = None,
            ordering: Optional[str] = None,
            offset: int = 0,
            limit: int = 10,
    ) -> tuple[list[UserInDB], int, int]:
        """Returns tuple: (list of pydantic models, total, total_pages)."""
        order_column, order_direction = parse_ordering(ordering, field_map=self.field_map)

        entities, total = await self._repo.get_all(
            search=search,
            is_mentor=is_mentor,
            is_team_member=is_team_member,
            order_column=order_column,
            order_direction=order_direction,
            offset=offset,
            limit=limit,
            mentor_join=True,
            participant_join=True,
            team_join=True if is_team_member is not None else False,
        )

        users_in_db = [
            UserInDB.model_construct(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                is_mentor=user.is_mentor,
                participant=user.participant,
                mentor=user.mentor,
                verified=user.verified,
                photo_path=user.photo_path,
            ) for user in entities
        ]

        total_pages = ceil(total / limit) if total > 0 else 1

        return users_in_db, total, total_pages

    async def get_by_id(self, user_id: int, join_team: bool = False) -> UserInDB:
        user = await self._repo.get_by_id(user_id, join_team)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found.'
            )
        team_id = None
        participant = user.participant
        if participant:
            team_id = participant.team_members.team_id
        return UserInDBWithTeamID.model_construct(
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            is_mentor=user.is_mentor,
            participant=user.participant,
            mentor=user.mentor,
            verified=user.verified,
            photo_path=user.photo_path,
            team_id=team_id
        )

    async def get_by_email(self, email: str) -> UserInDB:
        user = await self._repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        return UserInDB.model_construct(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            is_mentor=user.is_mentor,
            participant=user.participant,
            mentor=user.mentor,
            verified=user.verified,
            photo_path=user.photo_path,
        )

    async def create(self, user: UserCreate) -> UserInDB:
        try:
            participant_data, mentor_data = user.participant, user.mentor
            user = user.model_copy(update={'participant': None, 'mentor': None})
            user.password = PasswordEncryption.hash_password(user.password)
            if user.is_mentor:
                user, mentor = await self._repo.create_user_and_mentor(user, mentor_data)
                user_model = UserInDB.model_construct(
                    id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    email=user.email,
                    is_mentor=user.is_mentor,
                    participant=user.participant,
                    mentor=user.mentor,
                    verified=user.verified,
                    photo_path=user.photo_path,
                )
                user_model.mentor = MentorInDB.model_construct(
                    id=mentor.id,
                    is_admin=mentor.is_admin,
                    specialization=mentor.specialization,
                    job_title=mentor.job_title,
                    research_topics=mentor.research_topics,
                    articles=mentor.articles,
                    scientific_interests=mentor.scientific_interests,
                    taught_subjects=mentor.taught_subjects,
                )
            else:
                user, participant = await self._repo.create_user_and_participant(user, participant_data)
                user_model = UserInDB.model_construct(
                    id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    email=user.email,
                    is_mentor=user.is_mentor,
                    participant=user.participant,
                    mentor=user.mentor,
                    verified=user.verified,
                    photo_path=user.photo_path,
                )
                user_model.participant = ParticipantInDB.model_construct(
                    id=participant.id,
                    region_id=participant.region_id,
                    school_grade=participant.school_grade,
                    city=participant.city,
                    interests=participant.interests,
                    olympics=participant.olympics,
                    achievements=participant.achievements,
                )
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

        if photo == '' or photo:
            if current_user.photo_path:
                old_user_photo_full_path = await FileService.construct_full_path_from_relative_path(
                    current_user.photo_path
                )
                await FileService.delete_file_from_fs(old_user_photo_full_path)
                update_data['photo_path'] = None

        file_full_path = ''

        if photo:
            result = await FileService.upload_file(
                file=photo,
                path_segments=['photos', str(user_id)],
                allowed_mime_types=['image/jpeg', 'image/png', 'image/bmp'],
                size_limit_megabytes=10,
            )
            update_data['photo_path'] = result.relative_path
            file_full_path = result.full_path

        try:
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
                commit = False if participant_data or mentor_data else True
                current_user = await self._repo.update_user(
                    user_id=user_id,
                    update_data=main_fields,
                    commit=commit
                )

            if participant_data and not current_user.is_mentor:
                try:
                    current_user.participant = await self._repo.update_participant(
                        user_id=user_id,
                        update_data=participant_data,
                        commit=True
                    )
                except IntegrityError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail='Region does not exist.'
                    )

            if mentor_data and current_user.is_mentor:
                current_user.mentor = await self._repo.update_mentor(
                    user_id=user_id,
                    update_data=mentor_data,
                    commit=True,
                )
        except Exception as e:
            if file_full_path:
                await FileService.delete_file_from_fs(file_full_path)
            raise e

        return UserInDB.model_construct(
            id=current_user.id,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            is_mentor=current_user.is_mentor,
            participant=current_user.participant,
            mentor=current_user.mentor,
            verified=current_user.verified,
            photo_path=current_user.photo_path,
        )

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
            subject=SUCCESSFUL_REGISTRATION_EMAIL_SUBJECT,
            message=SUCCESSFUL_REGISTRATION_EMAIL_MESSAGE
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
            subject=REJECTED_REGISTRATION_EMAIL_SUBJECT,
            message=REJECTED_REGISTRATION_EMAIL_MESSAGE
        )  # type: ignore

    async def delete(self, user_id: int) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found.'
            )
        if user.is_mentor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Cannot delete mentor user.'
            )
        await self._repo.delete(user)
        await FileService.delete_all_files_in_directory(
            ['documents', str(user_id)]
        )
        await FileService.delete_all_files_in_directory(
            ['photos', str(user_id)]
        )

    async def download_users_info(self, background_tasks: BackgroundTasks) -> FileResponse:

        FILE_NAME = 'users.txt'
        txt_data: str = ''
        users_data: Sequence[User] = []
        users_data, _ = await self._repo.get_all(
            team_members_join=True,
            participant_join=True,
            mentor_join=True,
            region_join=True,
            team_join=True,
        )
        for user_data in users_data:
            txt_data += f'Пользователь с ID {user_data.id}:\n' + dict_to_text(
                {
                    'ФИО': f'{user_data.last_name} {user_data.patronymic} {user_data.first_name}',
                    'День рождения': f'{user_data.birth_date}',
                    'Email': f'{user_data.email}',
                    'Номер телефона': f'{user_data.phone_number}',
                    'Образовательная организация': f'{user_data.edu_organization}',
                    'Верификация': 'Верифицирован' if user_data.verified else 'Не верифицирован',
                    'О себе': f'{user_data.about}',
                    'Тип пользователя': 'Участник' if user_data.participant else 'Ментор',
                    'Регион': f'{user_data.participant.region.name}' if user_data.participant else None,
                    'Класс': f'{user_data.participant.school_grade}' if user_data.participant else None,
                    'Город': f'{user_data.participant.city}' if user_data.participant else None,
                    'Интересы': f'{user_data.participant.interests}' if user_data.participant else None,
                    'Олимпиады': f'{user_data.participant.olympics}' if user_data.participant else None,
                    'Достижения': f'{user_data.participant.achievements}' if user_data.participant else None,
                    'Направление': f'{user_data.mentor.specialization}' if user_data.mentor else None,
                    'Должность': f'{user_data.mentor.job_title}' if user_data.mentor else None,
                    'Статьи': f'{user_data.mentor.articles}' if user_data.mentor else None,
                    'Научные интересы': f'{user_data.mentor.scientific_interests}' if user_data.mentor else None,
                    'Преподаваемые предметы': f'{user_data.mentor.taught_subjects}' if user_data.mentor else None,
                    'Тематика НИР': f'{user_data.mentor.research_topics}' if user_data.mentor else None,
                }
            ) + '\n'
        file_path = await FileService.create_response_file(
            text=txt_data,
            file_name=FILE_NAME
        )
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        background_tasks.add_task(FileService.delete_file_from_fs, file_path)
        return FileResponse(
            path=str(file_path),
            filename=FILE_NAME,
            media_type='text/plain'
        )


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
        return UserDocumentInDB.model_construct(
            id=document.id,
            name=document.name,
            path=document.path,
            size=document.size,
            mimetype=document.mimetype,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    async def get_user_documents(self, user_id: int) -> list[UserDocumentInDB]:
        documents = await self._repo.get_user_documents(user_id)
        return [
            UserDocumentInDB.model_construct(
                id=document.id,
                name=document.name,
                path=document.path,
                size=document.size,
                mimetype=document.mimetype,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
            for document in documents
        ]

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
        try:
            document = await self._repo.create(
                user_id=user_id,
                path=result.relative_path,
                name=result.name,
                size=result.size_bytes,
                mimetype=result.mime_type,
            )
            return UserDocumentInDB.model_construct(
                id=document.id,
                name=document.name,
                path=document.path,
                size=document.size,
                mimetype=document.mimetype,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
        except Exception as e:
            await FileService.delete_file_from_fs(result.full_path)
            raise e

    async def delete(self, document_id: int, document: UserDocument) -> None:
        await self._repo.delete(document_id)
        full_path = await FileService.construct_full_path_from_relative_path(document.path)
        await FileService.delete_file_from_fs(full_path)


class RegionService:
    def __init__(self, repo: RegionRepo):
        self._repo = repo

    async def get_all(self, search: Optional[str], name: Optional[str], code: Optional[int]) -> list[RegionInDB]:
        regions = await self._repo.get_all(search, name, code)
        return [
            RegionInDB.model_construct(
                id=region.id,
                name=region.name,
                code=region.code
            )
            for region in regions
        ]
