import os
import re
import traceback
import zipfile
import magic
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Literal, Optional, Type, Union

import aiofiles
import aiosmtplib as aiosmtp
from fastapi import File, HTTPException, UploadFile, status
from pydantic import BaseModel

from settings import BASE_DIR, settings


def validate_password(password: str) -> None:
    if ' ' in password:
        raise ValueError('Password must not contain spaces')
    if not re.fullmatch(r'[A-Za-z0-9!@#$%&*]+', password):
        raise ValueError(
            'Password contains invalid characters. '
            'Allowed characters: uppercase and lowercase Latin letters, digits, and ! @ # $ % & *'
        )
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[!@#$%&*]', password):
        raise ValueError('Password must contain at least one special character (!@#$%&*)')


def create_field_map_for_model(model: Type[BaseModel]) -> dict[str, str]:
    """
    Create a bidirectional field map for the given Pydantic model.

    The map will contain:
    - snake_case field_name => snake_case field_name
    - camelCase alias => snake_case field_name

    This lets us convert either the snake_case or the camelCase alias
    into the correct snake_case database column name.

    :param model: A Pydantic model class (e.g., PartnerInDB).
    :return: A dictionary where keys are either the snake_case or camelCase alias,
             and values are the final snake_case name used in the DB.
    """
    field_map = {}
    for field_name, model_field in model.model_fields.items():
        # Example:
        #   field_name = "last_name"
        #   model_field.alias = "lastName"
        field_map[field_name] = field_name
        if model_field.alias != field_name:
            field_map[model_field.alias] = field_name
    return field_map


def parse_ordering(
        ordering: Optional[str],
        field_map: dict[str, str],
        default_field: str = 'id'
) -> tuple[str, Literal['ASC', 'DESC']]:
    """
    Parse an ordering string to determine the actual DB column and direction.

    The ordering string may be:
    - A field name (e.g., "name")
    - With or without a leading '-' to denote descending order.

    :param ordering: e.g., "-name", "id"
    :param field_map: A dict from create_field_map_for_model() that maps
                      both snake_case and camelCase to the final DB column name.
    :param default_field: Fallback column name if ordering is invalid.
    :return: A tuple: (column_name_in_snake_case, direction)
             where direction is "ASC" or "DESC".
    """
    if not ordering:
        # No ordering given; use default
        return default_field, 'ASC'

    descending = ordering.startswith('-')
    if descending:
        ordering = ordering[1:]  # remove '-'

    column_name = field_map.get(ordering, default_field)

    direction: Literal['ASC', 'DESC'] = 'DESC' if descending else 'ASC'

    return column_name, direction


async def send_mail(
        to_email: str,
        subject: str,
        message: str,
        from_email: str = settings.email.EMAIL_HOST_USER
):
    try:
        message_obj = EmailMessage()
        message_obj['From'] = from_email
        message_obj['To'] = to_email
        message_obj['Subject'] = subject
        message_obj.set_content(message)
        await aiosmtp.send(
            message_obj,
            hostname=settings.email.EMAIL_HOST,
            port=settings.email.EMAIL_PORT,
            username=settings.email.EMAIL_HOST_USER,
            password=settings.email.EMAIL_HOST_PASSWORD,
            use_tls=settings.email.EMAIL_USE_SSL,
        )
    except Exception:
        print('Could not send email: {}'.format(traceback.format_exc()))


@dataclass(frozen=True)
class FileUploadResult:
    full_path: Path
    relative_path: str
    mime_type: str
    size_bytes: int
    name: str


class FileService:
    @staticmethod
    def create_parse_optional_file(field_name: str):

        async def parse_optional_file(
                file: Union[UploadFile, str, None] = File(None, alias=field_name)
        ) -> Union[UploadFile, str, None]:
            if isinstance(file, str):
                return ''
            return file

        return parse_optional_file

    @staticmethod
    async def construct_full_path_from_relative_path(relative_path: str) -> Path:
        safe_file_path = relative_path.lstrip('/\\')
        return BASE_DIR / safe_file_path

    @staticmethod
    async def get_doc_path(instance_id: int, document_name: str, is_project: bool) -> Path:
        """
        Get the full path to a document in the filesystem.

        Args:
            instance_id: int - ID of the project or user
            document_name: str - Name of the document
            is_project: bool - Whether the document is a project document or user document
        Returns:
            Path: Full path to the document in the filesystem
        """

        if is_project:
            folder_name = 'projects'
        else:
            folder_name = 'users'
        safe_file_path = f'media/{folder_name}/{instance_id}/{document_name}'.lstrip('/\\')
        return BASE_DIR / safe_file_path

    @staticmethod
    def get_media_folder_path(instance_id: int, is_project: bool) -> Path:
        if is_project:
            folder_name = 'projects'
        else:
            folder_name = 'users'
        return BASE_DIR / f'media/{folder_name}/{instance_id}'

    @staticmethod
    async def delete_file_from_fs(full_path: Path) -> None:
        if full_path.exists():
            full_path.unlink()

    @staticmethod
    async def delete_all_files_in_directory(path_segments: list[str]) -> None:
        """
        Deletes all files in the specified directory.

        :param path_segments: list of path segments forming the directory path.
        """
        media_dir = BASE_DIR / settings.MEDIA_DIR
        for path_segment in path_segments:
            media_dir = media_dir / path_segment

        if not media_dir.exists() or not media_dir.is_dir():
            return

        for file in media_dir.iterdir():
            if file.is_file():
                file.unlink()

    @staticmethod
    async def upload_file(
            file: UploadFile,
            path_segments: list[str],
            allowed_mime_types: list[str],
            size_limit_megabytes: int,
    ) -> FileUploadResult:
        """
        Helper function to validate and upload file in the filesystem.

        1) Validate file type
        2) Validate file size
        3) Construct full Path object
        4) Write a file
        5) Return FileUploadResult

        :param path_segments: list of path segments. E.g., if we want to store a photo
                              of user with id 1, we will pass ['photos', '1'])
        :param file: UploadFile to be uploaded
        :param allowed_mime_types: list of allowed MIME types. E.g., ['image/jpeg', 'image/png', 'image/gif']
                                   (https://developer.mozilla.org/en-US/docs/Web/HTTP/MIME_types/Common_types)
        :param size_limit_megabytes: int
        :return: FileUploadResult obj.
        """
        file_name = file.filename

        content = await file.read()
        mime_type = magic.from_buffer(content[:4096], mime=True)
        if mime_type not in allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f'Invalid file format. Allowed formats: {", ".join(allowed_mime_types)}'
            )
        file_size = len(content)
        if file_size > size_limit_megabytes * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f'File size exceeds the limit of {size_limit_megabytes} MB'
            )
        await file.seek(0)
        media_dir = BASE_DIR / settings.MEDIA_DIR
        for path_segment in path_segments:
            media_dir = media_dir / path_segment
            media_dir.mkdir(parents=True, exist_ok=True)

        full_path = (media_dir / file_name).resolve()
        if full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'File with filename {file_name} already exists.'
            )

        async with aiofiles.open(full_path, 'wb') as out_file:
            await out_file.write(content)

        relative_path = f'{str(settings.MEDIA_DIR)}/' + '/'.join(path_segments) + f'/{file_name}'
        return FileUploadResult(
            full_path=full_path,
            relative_path=relative_path,
            mime_type=mime_type,
            size_bytes=file_size,
            name=file_name
        )

    async def create_zip_from_directory(folder_path: Path, text: str) -> Path:
        zip_path = folder_path.parent / (folder_path.name + '.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip_file.write(file_path, os.path.relpath(file_path, folder_path))
            zip_file.writestr('Описание_проекта.txt', text)
        return zip_path


def clean_errors(errors: list[dict]) -> list[dict]:
    for err in errors:
        if 'ctx' in err and 'error' in err['ctx']:
            err.pop('ctx')
        if 'url' in err:
            err.pop('url', None)
    return errors
