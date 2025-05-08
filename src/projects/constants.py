from enum import Enum
from typing import Literal


class ProjectStatus(str, Enum):
    NOT_STARTED = 'Not started'
    IN_PROGRESS = 'In progress'
    SUBMITTED = 'Submitted for review'
    ACCEPTED = 'Accepted'
    TIME_EXCEEDED = 'Time exceeded'


PROJECT_FILES_MIME_TYPES = [
    "image/jpeg",  # JPEG (JPG)
    "image/png",   # PNG
    "image/bmp",   # BMP

    "application/pdf",  # PDF
    "application/rtf",  # RTF
    "application/vnd.oasis.opendocument.text",  # ODT
    "text/plain",  # TXT
    "application/msword",  # DOC
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX

    "application/vnd.ms-excel",  # XLS
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
    "application/vnd.oasis.opendocument.spreadsheet",  # ODS
    "text/csv",  # CSV

    "application/vnd.ms-powerpoint",  # PPT
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX

    "video/mp4",  # MP4
    "audio/mpeg",  # MP3
    "video/x-msvideo",  # AVI
    "video/quicktime",  # MOV
    "video/x-ms-wmv",  # WMV
    "audio/wav",  # WAV
    "video/mpeg",  # MPEG
    "video/x-flv",  # FLV
    "audio/aac",  # AAC
    "audio/basic",  # AU

    "application/x-7z-compressed",  # 7z
    "application/x-rar-compressed",  # RAR
    "application/zip",  # ZIP

    "image/vnd.adobe.photoshop",  # PSD
    "application/x-coreldraw",  # CDR
    "application/postscript",  # AI, EPS
    "model/stl"  # STL
]

MODIFY_STEP_ACTIONS = Literal['set-timer', 'accept', 'reject']
