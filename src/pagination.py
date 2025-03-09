from typing import Generic, List, TypeVar

from fastapi import Query
from schemas import ConfiguredModel
from settings import settings

T = TypeVar('T')


class PaginationParams:
    def __init__(
            self,
            page: int = Query(
                1,
                ge=1,
                description='Page number'
            ),
            per_page: int = Query(
                settings.DEFAULT_ELEMENTS_PER_PAGE,
                ge=1,
                le=settings.MAX_ELEMENTS_PER_PAGE,
                description='Amount of elements per page'
            )
    ):
        self.page = page
        self.per_page = per_page

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(ConfiguredModel, Generic[T]):
    page: int
    per_page: int
    total_pages: int
    total: int
    items: List[T]
