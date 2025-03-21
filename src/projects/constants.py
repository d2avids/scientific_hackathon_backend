from enum import Enum


class ProjectStatus(str, Enum):
    NOT_STARTED = 'Not started'
    IN_PROGRESS = 'In progress'
    SUBMITTED = 'Submitted for review'
    ACCEPTED = 'Accepted'
    TIME_EXCEEDED = 'Time exceeded'
